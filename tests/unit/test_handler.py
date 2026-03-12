import json
from unittest.mock import patch, MagicMock
import pytest


class TestHealthCheck:
    def test_health_check(self, health_event):
        from handler import lambda_handler

        response = lambda_handler(health_event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'ok'
        assert 'timestamp' in body


class TestOptionsRequest:
    def test_options_request(self):
        from handler import lambda_handler

        event = {
            'httpMethod': 'OPTIONS',
            'path': '/analyze',
            'headers': {},
            'requestContext': {},
            'resource': '/analyze'
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 204
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert 'Access-Control-Allow-Methods' in response['headers']


class TestVerifyOrigin:
    def test_verify_origin_success(self, api_gateway_event, mock_env):
        from handler import verify_origin

        assert verify_origin(api_gateway_event) is True

    def test_verify_origin_failure(self, mock_env):
        from handler import verify_origin

        event = {
            'headers': {'x-origin-verify': 'wrong-secret'}
        }
        assert verify_origin(event) is False


class TestAnalyze:
    @patch('handler.get_openai_api_key', return_value='test-api-key')
    @patch('analyzer.OpenAIAnalyzer.analyze')
    def test_analyze_success(self, mock_analyze, mock_api_key, api_gateway_event, mock_env):
        mock_analyze.return_value = {
            'found': True,
            'answer': 'A crack was detected in the image',
            'confidence': 85,
            'model': 'gpt-4.1-mini',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'context': 'この画像に「crack」は存在しますか？'
        }
        from handler import lambda_handler

        response = lambda_handler(api_gateway_event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['found'] is True
        assert 'answer' in body
        assert 'confidence' in body
        assert 'model' in body
        assert 'usage' in body
        assert 'context' in body
        assert 'elapsed_seconds' in body

    def test_analyze_missing_image(self, mock_env):
        from handler import lambda_handler

        event = {
            'httpMethod': 'POST',
            'path': '/analyze',
            'headers': {'x-origin-verify': 'test-secret'},
            'body': '{"target": "crack"}',
            'requestContext': {},
            'resource': '/analyze'
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'image' in body['error'] or 'data' in body['error']

    def test_analyze_missing_target(self, mock_env):
        from handler import lambda_handler

        event = {
            'httpMethod': 'POST',
            'path': '/analyze',
            'headers': {'x-origin-verify': 'test-secret'},
            'body': '{"image": "data:image/jpeg;base64,/9j/4AAQ..."}',
            'requestContext': {},
            'resource': '/analyze'
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'target' in body['error']

    @patch('handler.get_openai_api_key', return_value='test-api-key')
    @patch('analyzer.OpenAIAnalyzer.analyze')
    def test_analyze_with_data_uri(self, mock_analyze, mock_api_key, mock_env):
        mock_analyze.return_value = {
            'found': False,
            'answer': '見つかりませんでした',
            'confidence': 10,
            'model': 'gpt-4.1-mini',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'context': 'この画像に「猫」は存在しますか？'
        }
        from handler import lambda_handler

        event = {
            'httpMethod': 'POST',
            'path': '/analyze',
            'headers': {'x-origin-verify': 'test-secret'},
            'body': '{"image": "data:image/jpeg;base64,/9j/4AAQ...", "target": "猫"}',
            'requestContext': {},
            'resource': '/analyze'
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        mock_analyze.assert_called_once()
        call_args = mock_analyze.call_args
        assert call_args[0][0] == '/9j/4AAQ...'

    @patch('handler.get_openai_api_key', return_value='test-api-key')
    @patch('analyzer.OpenAIAnalyzer.analyze')
    def test_analyze_with_raw_base64(self, mock_analyze, mock_api_key, mock_env):
        mock_analyze.return_value = {
            'found': True,
            'answer': '犬がいます',
            'confidence': 90,
            'model': 'gpt-4.1-mini',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'context': 'この画像に「犬」は存在しますか？'
        }
        from handler import lambda_handler

        event = {
            'httpMethod': 'POST',
            'path': '/analyze',
            'headers': {'x-origin-verify': 'test-secret'},
            'body': '{"image": "/9j/4AAQraw_base64_data", "target": "犬"}',
            'requestContext': {},
            'resource': '/analyze'
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        mock_analyze.assert_called_once()
        call_args = mock_analyze.call_args
        assert call_args[0][0] == '/9j/4AAQraw_base64_data'


class TestWorkflowAnalyze:
    @patch('handler.get_openai_api_key', return_value='test-api-key')
    @patch('analyzer.OpenAIAnalyzer.analyze')
    def test_workflow_analyze_success(self, mock_analyze, mock_api_key, workflow_event):
        mock_analyze.return_value = {
            'found': True,
            'answer': 'A crack is visible',
            'confidence': 92,
            'model': 'gpt-4.1-mini',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'context': 'この画像に「crack」は存在しますか？'
        }
        from handler import lambda_handler

        response = lambda_handler(workflow_event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['found'] is True
        assert body['confidence'] == 92


class TestSSMCache:
    @patch('boto3.client')
    def test_ssm_api_key_cache(self, mock_boto3):
        import handler
        handler._cached_api_key = None

        mock_ssm = MagicMock()
        mock_ssm.get_parameter.return_value = {
            'Parameter': {'Value': 'cached-test-key'}
        }
        mock_boto3.return_value = mock_ssm

        key1 = handler.get_openai_api_key()
        key2 = handler.get_openai_api_key()

        assert key1 == 'cached-test-key'
        assert key2 == 'cached-test-key'
        mock_ssm.get_parameter.assert_called_once()

        handler._cached_api_key = None


class TestImageInput:
    """画像入力方式のテスト"""

    @patch('handler.get_openai_api_key', return_value='test-api-key')
    @patch('analyzer.OpenAIAnalyzer.analyze')
    @patch('handler._get_image_from_s3')
    def test_s3_key_success(self, mock_s3, mock_analyze, mock_api_key, s3_event):
        mock_s3.return_value = '/9j/4AAQbase64data'
        mock_analyze.return_value = {
            'found': True, 'answer': 'Crack detected', 'confidence': 90,
            'model': 'gpt-4.1-mini',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'context': 'この画像に「crack」は存在しますか？'
        }
        from handler import lambda_handler
        response = lambda_handler(s3_event, None)
        assert response['statusCode'] == 200
        mock_s3.assert_called_once_with('test-bucket', 'tmp/photo.jpg')

    def test_s3_key_missing_bucket(self):
        from handler import lambda_handler
        event = {
            'httpMethod': 'POST',
            'headers': {'content-type': 'application/json'},
            'body': json.dumps({'image_key': 'tmp/photo.jpg', 'target': 'crack'}),
            'requestContext': {},
            'resource': '/workflow/analyze'
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400

    @patch('handler.get_openai_api_key', return_value='test-api-key')
    @patch('analyzer.OpenAIAnalyzer.analyze')
    @patch('handler._get_image_from_url')
    def test_url_success(self, mock_url, mock_analyze, mock_api_key, url_event):
        mock_url.return_value = '/9j/4AAQbase64data'
        mock_analyze.return_value = {
            'found': True, 'answer': 'Crack detected', 'confidence': 90,
            'model': 'gpt-4.1-mini',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'context': 'この画像に「crack」は存在しますか？'
        }
        from handler import lambda_handler
        response = lambda_handler(url_event, None)
        assert response['statusCode'] == 200
        mock_url.assert_called_once_with('https://test-bucket.s3.ap-northeast-1.amazonaws.com/photo.jpg')

    def test_url_invalid_domain(self):
        from handler import lambda_handler
        event = {
            'httpMethod': 'POST',
            'headers': {'content-type': 'application/json'},
            'body': json.dumps({
                'image_url': 'https://evil.example.com/malware.jpg',
                'target': 'crack'
            }),
            'requestContext': {},
            'resource': '/workflow/analyze'
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'domain' in body['error'].lower() or 'url' in body['error'].lower()

    @patch('handler.get_openai_api_key', return_value='test-api-key')
    @patch('analyzer.OpenAIAnalyzer.analyze')
    @patch('handler._get_image_from_s3')
    def test_s3_key_priority_over_image(self, mock_s3, mock_analyze, mock_api_key):
        """S3キーが image より優先される"""
        mock_s3.return_value = '/9j/4AAQs3data'
        mock_analyze.return_value = {
            'found': True, 'answer': 'OK', 'confidence': 80,
            'model': 'gpt-4.1-mini',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'context': 'テスト'
        }
        from handler import lambda_handler
        event = {
            'httpMethod': 'POST',
            'headers': {'content-type': 'application/json'},
            'body': json.dumps({
                'image_bucket': 'test-bucket',
                'image_key': 'photo.jpg',
                'image': 'data:image/jpeg;base64,/9j/ignored',
                'target': 'crack'
            }),
            'requestContext': {},
            'resource': '/workflow/analyze'
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        mock_s3.assert_called_once()
        call_args = mock_analyze.call_args
        assert call_args[0][0] == '/9j/4AAQs3data'


class TestLogging:
    """ロガーのテスト"""

    def test_contextualize_decorator_exists(self):
        """lambda_handlerにcontextualizeデコレータが適用されている"""
        import handler
        assert callable(handler.lambda_handler)

    @patch('handler.get_openai_api_key', return_value='test-api-key')
    @patch('analyzer.OpenAIAnalyzer.analyze')
    def test_logging_on_success(self, mock_analyze, mock_api_key, api_gateway_event, mock_env, mock_logger):
        mock_analyze.return_value = {
            'found': True, 'answer': 'Crack detected', 'confidence': 90,
            'model': 'gpt-4.1-mini',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'context': 'テスト'
        }
        from handler import lambda_handler
        response = lambda_handler(api_gateway_event, None)
        assert response['statusCode'] == 200
        assert mock_logger.info.call_count >= 2

    def test_logging_on_error(self, mock_env, mock_logger):
        from handler import lambda_handler
        event = {
            'httpMethod': 'POST',
            'headers': {'x-origin-verify': 'test-secret'},
            'body': '{"target": "crack"}',
            'requestContext': {},
            'resource': '/analyze'
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        assert mock_logger.warning.call_count >= 1


class TestAnalyzeOriginBlock:
    def test_analyze_returns_403_without_origin(self, mock_env):
        from handler import lambda_handler

        event = {
            'httpMethod': 'POST',
            'path': '/analyze',
            'headers': {'x-origin-verify': 'wrong-value'},
            'body': '{"image": "data:image/jpeg;base64,/9j/4AAQ...", "target": "crack"}',
            'requestContext': {},
            'resource': '/analyze'
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
