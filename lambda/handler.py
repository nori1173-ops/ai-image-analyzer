import base64
import json
import os
import re
import time
from urllib.parse import urlparse
from urllib.request import urlopen, Request
import boto3
from aws_lambda_powertools import Logger

logger = Logger()

_cached_api_key = None


def get_openai_api_key():
    global _cached_api_key
    if _cached_api_key:
        return _cached_api_key
    ssm_path = os.environ.get('SSM_OPENAI_API_KEY_PATH', '/image-analysis/openai-api-key')
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(Name=ssm_path, WithDecryption=True)
    _cached_api_key = response['Parameter']['Value']
    return _cached_api_key


def verify_origin(event):
    verify_value = os.environ.get('ORIGIN_VERIFY_VALUE', '')
    if not verify_value:
        return True
    verify_header = os.environ.get('ORIGIN_VERIFY_HEADER', 'x-origin-verify')
    headers = event.get('headers') or {}
    header_value = (
        headers.get(verify_header.lower(), '')
        or headers.get(verify_header, '')
    )
    return header_value == verify_value


def _is_allowed_url(url):
    parsed = urlparse(url)
    return parsed.hostname and parsed.hostname.endswith('.amazonaws.com')


def _get_image_from_s3(bucket, key):
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket, Key=key)
    image_bytes = response['Body'].read()
    return base64.b64encode(image_bytes).decode('utf-8')


def _get_image_from_url(url):
    req = Request(url)
    req.add_header('User-Agent', 'ImageAnalysisAPI/1.0')
    with urlopen(req, timeout=10) as resp:
        image_bytes = resp.read(20 * 1024 * 1024 + 1)
        if len(image_bytes) > 20 * 1024 * 1024:
            raise ValueError('Image too large (max 20MB)')
    return base64.b64encode(image_bytes).decode('utf-8')


def extract_base64_image(body):
    image_bucket = body.get('image_bucket', '')
    image_key = body.get('image_key', '')
    image_url = body.get('image_url', '')
    image = body.get('image', '')
    data = body.get('data', '')

    if image_bucket or image_key:
        if not image_bucket or not image_key:
            return None, 'image_bucket and image_key are both required'
        return _get_image_from_s3(image_bucket, image_key), None
    elif image_url:
        if not _is_allowed_url(image_url):
            return None, 'URL domain not allowed. Only *.amazonaws.com domains are accepted'
        return _get_image_from_url(image_url), None
    elif image:
        match = re.match(r'data:image/[^;]+;base64,(.+)', image)
        if match:
            return match.group(1), None
        return image, None
    elif data:
        return data, None
    return None, 'image, data, image_url, or image_bucket+image_key is required'


@logger.inject_lambda_context
def lambda_handler(event, context):
    cors_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key'
    }

    http_method = event.get('httpMethod', '')
    resource = event.get('resource', '')

    logger.info("リクエストを受信しました。", resource=resource, method=http_method)

    if http_method == 'OPTIONS':
        return {'statusCode': 204, 'headers': cors_headers, 'body': ''}

    if resource == '/health' and http_method == 'GET':
        from datetime import datetime, timezone
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'status': 'ok',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }

    if resource == '/analyze':
        if not verify_origin(event):
            logger.warning("オリジン検証に失敗しました。", resource=resource)
            return {
                'statusCode': 403,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Forbidden'})
            }

    if http_method == 'POST' and resource in ('/analyze', '/workflow/analyze'):
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            logger.warning("不正なJSONを受信しました。")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid JSON'})
            }

        base64_image, error = extract_base64_image(body)
        if error:
            logger.warning("画像入力エラー", error=error)
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': error})
            }
        if not base64_image:
            logger.warning("画像データが指定されていません。")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'image or data is required'})
            }

        target = body.get('target', '').strip()
        if not target:
            logger.warning("targetが指定されていません。")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'target is required'})
            }

        model = body.get('model', 'gpt-4.1-mini')
        detail = body.get('detail', 'low')

        logger.info("解析を開始します。", model=model, detail=detail, target=target)

        start_time = time.time()

        from analyzer import get_analyzer
        api_key = get_openai_api_key()
        analyzer = get_analyzer(api_key)
        result = analyzer.analyze(base64_image, target, model, detail)

        elapsed = round(time.time() - start_time, 2)
        result['elapsed_seconds'] = elapsed

        logger.info("解析が完了しました。", model=model, elapsed_seconds=elapsed,
                    target=target, found=result.get('found'), confidence=result.get('confidence'))

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(result, ensure_ascii=False)
        }

    return {
        'statusCode': 404,
        'headers': cors_headers,
        'body': json.dumps({'error': 'Not Found'})
    }
