import base64
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
import boto3
from example_powertools.logging import LambdaLogger
from model_resolver import GRADES as MODEL_GRADES, resolve_model

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
    if parsed.scheme != 'https':
        return False
    return bool(parsed.hostname) and parsed.hostname.endswith('.amazonaws.com')


def _is_allowed_bucket(bucket):
    allowed = os.environ.get('ALLOWED_IMAGE_BUCKETS', '')
    allowed_buckets = [b.strip() for b in allowed.split(',') if b.strip()]
    return bucket in allowed_buckets


def _get_image_from_s3(bucket, key):
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket, Key=key)
    image_bytes = response['Body'].read()
    return base64.b64encode(image_bytes).decode('utf-8')


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _get_image_from_url(url):
    req = Request(url)
    req.add_header('User-Agent', 'ImageAnalysisAPI/1.0')
    opener = build_opener(_NoRedirectHandler)
    try:
        with opener.open(req, timeout=10) as resp:
            image_bytes = resp.read(20 * 1024 * 1024 + 1)
    except HTTPError as e:
        if 300 <= e.code < 400:
            raise ValueError('リダイレクトは許可されていません')
        raise ValueError(f'画像の取得に失敗しました (HTTP {e.code})')
    if len(image_bytes) > 20 * 1024 * 1024:
        raise ValueError('Image too large (max 20MB)')
    return base64.b64encode(image_bytes).decode('utf-8')


def extract_base64_image(body, prefix=''):
    image_bucket = body.get(prefix + 'image_bucket', '')
    image_key = body.get(prefix + 'image_key', '')
    image_url = body.get(prefix + 'image_url', '')
    image = body.get(prefix + 'image', '')
    data = body.get(prefix + 'data', '')

    if image_bucket or image_key:
        if not image_bucket or not image_key:
            return None, f'{prefix}image_bucket and {prefix}image_key are both required'
        if not _is_allowed_bucket(image_bucket):
            raise ValueError('指定されたバケットは許可されていません')
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
    return None, f'{prefix}image, {prefix}data, {prefix}image_url, or {prefix}image_bucket+{prefix}image_key is required'


VALID_EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max')
NOTIFY_RECIPIENT_FIELDS = ('notify_to', 'notify_cc', 'notify_bcc')
EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
LINE_IMAGE_MAX_BYTES = 1_048_576


def _is_valid_model(model):
    return model.startswith(('claude', 'anthropic.claude', 'openai.gpt'))


def _resolve_request_model(body, logger):
    """model明示 > grade解決（ai-model-selector） > DEFAULT_MODEL の順で決定する。"""
    model = body.get('model')
    if model:
        return model, None
    grade = body.get('grade')
    if grade is not None:
        if grade not in MODEL_GRADES:
            return None, 'Invalid grade (high|standard|low)'
        resolved, source = resolve_model(grade)
        if resolved:
            logger.info("グレードからモデルを解決しました。", {
                "grade": grade, "model": resolved, "source": source})
            return resolved, None
        logger.warning("グレード解決に失敗したためデフォルトモデルを使用します。", {"grade": grade})
    return os.environ.get('DEFAULT_MODEL', 'anthropic.claude-sonnet-5'), None


def _is_valid_effort(effort):
    return effort is None or effort in VALID_EFFORTS


def _invalid_notify_recipient_field(body):
    for field in NOTIFY_RECIPIENT_FIELDS:
        if field not in body:
            continue
        recipients = body[field]
        if not isinstance(recipients, list) or len(recipients) > 10:
            return field
        if any(not isinstance(recipient, str) or not EMAIL_PATTERN.fullmatch(recipient)
               for recipient in recipients):
            return field
    return None


def _resolve_analyzer(model):
    from analyzer import get_analyzer
    return get_analyzer(model)


def _build_danger_notification_body(perspective, result):
    return (
        f"監視観点: {perspective}\n"
        f"危険度: {result.get('risk_level')}\n"
        f"判定理由: {result.get('reason')}\n"
        f"検出された変化: {result.get('changes')}\n"
        f"モデル: {result.get('model')}\n"
        f"判定時刻: {datetime.now(timezone.utc).isoformat()}"
    )


def _send_danger_notification(perspective, result, base64_before, base64_after,
                              to=None, cc=None, bcc=None):
    from analyzer import _detect_media_type
    from notifier import get_notifier

    subject = f'【画像解析】危険検知: {perspective}'
    body = _build_danger_notification_body(perspective, result)
    attachments = []
    for name, image in (('before', base64_before), ('after', base64_after)):
        media_type = _detect_media_type(image)
        attachments.append({
            'filename': f"{name}.{media_type.split('/')[1].replace('jpeg', 'jpg')}",
            'data': base64.b64decode(image),
            'content_type': media_type
        })
    return get_notifier().send(
        subject, body, attachments, to=to, cc=cc, bcc=bcc)


def _send_line_danger_notification(perspective, result, base64_before, base64_after):
    from analyzer import _detect_media_type
    from notifier import get_line_notifier

    line_notifier = get_line_notifier()
    bucket = os.environ.get('LINE_IMAGES_BUCKET', '')
    if not bucket:
        raise ValueError('LINE_IMAGES_BUCKETが設定されていません')

    s3 = boto3.client('s3')
    image_id = str(uuid.uuid4())
    image_urls = []
    sent_image_labels = []
    skipped_image_labels = []
    for name, label, image in (
            ('before', '前回', base64_before),
            ('after', '今回', base64_after)):
        image_data = base64.b64decode(image)
        if len(image_data) > LINE_IMAGE_MAX_BYTES:
            skipped_image_labels.append(label)
            continue
        media_type = _detect_media_type(image)
        extension = media_type.split('/')[1].replace('jpeg', 'jpg')
        key = f'line/{image_id}/{name}.{extension}'
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=image_data,
            ContentType=media_type,
        )
        image_urls.append(s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=21600,
        ))
        sent_image_labels.append(label)

    notes = []
    if sent_image_labels:
        image_positions = '/'.join(
            f'{index}枚目={label}'
            for index, label in enumerate(sent_image_labels, start=1))
        notes.append(f'画像{image_positions}、画像リンクは6時間で失効')
    if skipped_image_labels:
        skipped_images = '/'.join(
            f'{label}画像' for label in skipped_image_labels)
        notes.append(
            f'（{skipped_images}はサイズ超過のためLINE送信対象外。メール添付を参照）')

    text = _build_danger_notification_body(perspective, result)
    if notes:
        text = f"{text}\n\n{'\n'.join(notes)}"
    return line_notifier.send_line(text, image_urls)


@LambdaLogger.contextualize
def lambda_handler(event, context):
    logger = LambdaLogger()

    cors_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', '*'),
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key'
    }

    http_method = event.get('httpMethod', '')
    resource = event.get('resource', '')

    logger.info("リクエストを受信しました。", {
        "resource": resource,
        "method": http_method
    })

    if http_method == 'OPTIONS':
        return {'statusCode': 204, 'headers': cors_headers, 'body': ''}

    if resource in ('/health', '/analyze', '/compare'):
        if not verify_origin(event):
            logger.warning("オリジン検証に失敗しました。", {"resource": resource})
            return {
                'statusCode': 403,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Forbidden'})
            }

    if resource == '/health' and http_method == 'GET':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'status': 'ok',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
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

        try:
            base64_image, error = extract_base64_image(body)
        except ValueError as e:
            logger.warning("画像入力エラー", {"error": str(e)})
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': str(e)}, ensure_ascii=False)
            }
        if error:
            logger.warning("画像入力エラー", {"error": error})
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

        model, grade_error = _resolve_request_model(body, logger)
        if grade_error:
            logger.warning("許可されていないgradeです。", {"grade": body.get('grade')})
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': grade_error})
            }
        detail = body.get('detail', 'low')
        effort = body.get('effort')

        if not _is_valid_model(model):
            logger.warning("許可されていないモデル名です。", {"model": model})
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid model'})
            }

        if not _is_valid_effort(effort):
            logger.warning("許可されていないeffortです。", {"effort": effort})
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid effort (low|medium|high|xhigh|max)'})
            }

        logger.info("解析を開始します。", {
            "model": model,
            "detail": detail,
            "target": target
        })

        start_time = time.time()

        analyzer = _resolve_analyzer(model)
        result = analyzer.analyze(base64_image, target, model, detail, effort=effort)

        elapsed = round(time.time() - start_time, 2)
        result['elapsed_seconds'] = elapsed

        logger.info("解析が完了しました。", {
            "model": model,
            "elapsed_seconds": elapsed,
            "target": target,
            "found": result.get('found'),
            "confidence": result.get('confidence')
        })

        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(result, ensure_ascii=False)
        }

    if http_method == 'POST' and resource in ('/compare', '/workflow/compare'):
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            logger.warning("不正なJSONを受信しました。")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid JSON'})
            }

        invalid_notify_field = _invalid_notify_recipient_field(body)
        if invalid_notify_field:
            logger.warning("通知先メールアドレスが不正です。", {
                "field": invalid_notify_field
            })
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': f'Invalid {invalid_notify_field}'})
            }

        try:
            base64_before, before_error = extract_base64_image(body, 'before_')
            base64_after, after_error = extract_base64_image(body, 'after_')
        except ValueError as e:
            logger.warning("画像入力エラー", {"error": str(e)})
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': str(e)}, ensure_ascii=False)
            }
        if not base64_before:
            logger.warning("before画像が指定されていません。", {"error": before_error})
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': before_error or 'before image is required'})
            }
        if not base64_after:
            logger.warning("after画像が指定されていません。", {"error": after_error})
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': after_error or 'after image is required'})
            }

        perspective = body.get('perspective', '').strip()
        if not perspective:
            logger.warning("perspectiveが指定されていません。")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'perspective is required'})
            }

        model, grade_error = _resolve_request_model(body, logger)
        if grade_error:
            logger.warning("許可されていないgradeです。", {"grade": body.get('grade')})
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': grade_error})
            }
        detail = body.get('detail', 'low')
        effort = body.get('effort')
        notify = bool(body.get('notify', False))
        notify_to = body.get('notify_to') or None
        notify_cc = body.get('notify_cc')
        notify_bcc = body.get('notify_bcc')
        notify_line = bool(body.get('notify_line', False))

        if not _is_valid_model(model):
            logger.warning("許可されていないモデル名です。", {"model": model})
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid model'})
            }

        if not _is_valid_effort(effort):
            logger.warning("許可されていないeffortです。", {"effort": effort})
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid effort (low|medium|high|xhigh|max)'})
            }

        logger.info("画像比較を開始します。", {
            "model": model,
            "detail": detail,
            "perspective": perspective
        })

        start_time = time.time()

        analyzer = _resolve_analyzer(model)
        result = analyzer.compare(base64_before, base64_after, perspective, model, detail, effort=effort)

        elapsed = round(time.time() - start_time, 2)
        result['elapsed_seconds'] = elapsed

        logger.info("画像比較が完了しました。", {
            "model": model,
            "elapsed_seconds": elapsed,
            "perspective": perspective,
            "danger": result.get('danger'),
            "risk_level": result.get('risk_level')
        })

        notified = False
        if notify and result.get('danger'):
            try:
                send_result = _send_danger_notification(
                    perspective,
                    result,
                    base64_before,
                    base64_after,
                    to=notify_to,
                    cc=notify_cc,
                    bcc=notify_bcc,
                )
                result['message_id'] = send_result['message_id']
                notified = True
                logger.info("危険検知メールを送信しました。", {"message_id": send_result['message_id']})
            except Exception as e:
                logger.error("通知の送信に失敗しました。", {"error": str(e)})
                result['notify_error'] = str(e)
        result['notified'] = notified

        line_notified = False
        if notify_line and result.get('danger'):
            from notifier import LineNotConfiguredError
            try:
                _send_line_danger_notification(
                    perspective, result, base64_before, base64_after)
                line_notified = True
                logger.info("危険検知LINE通知を送信しました。")
            except LineNotConfiguredError as e:
                logger.warning("LINE通知をスキップしました。", {"reason": str(e)})
                result['line_skip_reason'] = str(e)
            except Exception as e:
                logger.error("LINE通知の送信に失敗しました。", {"error": str(e)})
                result['line_error'] = str(e)
        result['line_notified'] = line_notified

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
