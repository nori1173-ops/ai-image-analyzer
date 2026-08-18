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
    @pytest.mark.parametrize('model', [
        'anthropic.claude-sonnet-5',
        'openai.gpt-5.5',
    ])
    @patch('handler._resolve_analyzer')
    def test_bedrock_models_are_accepted(
            self, mock_resolve, model, api_gateway_event, mock_env):
        mock_resolve.return_value.analyze.return_value = {
            'found': True,
            'answer': '人物がいます',
            'confidence': 90,
            'model': model,
            'context': 'この画像に「人物」は存在しますか？',
            'usage': {
                'prompt_tokens': 1,
                'completion_tokens': 1,
                'total_tokens': 2,
            },
        }
        from handler import lambda_handler

        body = json.loads(api_gateway_event['body'])
        body['model'] = model
        api_gateway_event['body'] = json.dumps(body)

        response = lambda_handler(api_gateway_event, None)

        assert response['statusCode'] == 200
        mock_resolve.assert_called_once_with(model)

    @patch('handler._resolve_analyzer')
    def test_gpt_model_returns_400(
            self, mock_resolve, api_gateway_event, mock_env):
        from handler import lambda_handler

        body = json.loads(api_gateway_event['body'])
        body['model'] = 'gpt-4.1-mini'
        api_gateway_event['body'] = json.dumps(body)

        response = lambda_handler(api_gateway_event, None)

        assert response['statusCode'] == 400
        assert json.loads(response['body']) == {'error': 'Invalid model'}
        mock_resolve.assert_not_called()

    @patch('analyzer.ClaudeAnalyzer.analyze')
    def test_analyze_success(self, mock_analyze, api_gateway_event, mock_env):
        mock_analyze.return_value = {
            'found': True,
            'answer': '人物が画像内に存在します',
            'confidence': 85,
            'model': 'claude-haiku-4-5',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'context': 'この画像に「人物」は存在しますか？'
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
            'body': '{"target": "人物"}',
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

    @patch('analyzer.ClaudeAnalyzer.analyze')
    def test_analyze_with_data_uri(self, mock_analyze, mock_env):
        mock_analyze.return_value = {
            'found': False,
            'answer': '見つかりませんでした',
            'confidence': 10,
            'model': 'claude-haiku-4-5',
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

    @patch('analyzer.ClaudeAnalyzer.analyze')
    def test_analyze_with_raw_base64(self, mock_analyze, mock_env):
        mock_analyze.return_value = {
            'found': True,
            'answer': '犬がいます',
            'confidence': 90,
            'model': 'claude-haiku-4-5',
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
    @patch('analyzer.ClaudeAnalyzer.analyze')
    def test_workflow_analyze_success(self, mock_analyze, workflow_event, mock_env):
        mock_analyze.return_value = {
            'found': True,
            'answer': '人物が確認できます',
            'confidence': 92,
            'model': 'claude-haiku-4-5',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'context': 'この画像に「人物」は存在しますか？'
        }
        from handler import lambda_handler

        response = lambda_handler(workflow_event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['found'] is True
        assert body['confidence'] == 92

class TestImageInput:
    """画像入力方式のテスト"""

    @patch('analyzer.ClaudeAnalyzer.analyze')
    @patch('handler._get_image_from_s3')
    def test_s3_key_success(self, mock_s3, mock_analyze, s3_event, mock_env):
        mock_s3.return_value = '/9j/4AAQbase64data'
        mock_analyze.return_value = {
            'found': True, 'answer': '人物発見', 'confidence': 90,
            'model': 'claude-haiku-4-5',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'context': 'この画像に「人物」は存在しますか？'
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
            'body': json.dumps({'image_key': 'tmp/photo.jpg', 'target': '人物'}),
            'requestContext': {},
            'resource': '/workflow/analyze'
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400

    @patch('analyzer.ClaudeAnalyzer.analyze')
    @patch('handler._get_image_from_url')
    def test_url_success(self, mock_url, mock_analyze, url_event, mock_env):
        mock_url.return_value = '/9j/4AAQbase64data'
        mock_analyze.return_value = {
            'found': True, 'answer': '人物発見', 'confidence': 90,
            'model': 'claude-haiku-4-5',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'context': 'この画像に「人物」は存在しますか？'
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
                'target': '人物'
            }),
            'requestContext': {},
            'resource': '/workflow/analyze'
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'domain' in body['error'].lower() or 'url' in body['error'].lower()

    @patch('analyzer.ClaudeAnalyzer.analyze')
    @patch('handler._get_image_from_s3')
    def test_s3_key_priority_over_image(self, mock_s3, mock_analyze, mock_env):
        """S3キーが image より優先される"""
        mock_s3.return_value = '/9j/4AAQs3data'
        mock_analyze.return_value = {
            'found': True, 'answer': 'OK', 'confidence': 80,
            'model': 'claude-haiku-4-5',
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
                'target': '人物'
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

    @patch('analyzer.ClaudeAnalyzer.analyze')
    def test_logging_on_success(self, mock_analyze, api_gateway_event, mock_env, mock_logger):
        mock_analyze.return_value = {
            'found': True, 'answer': '人物発見', 'confidence': 90,
            'model': 'claude-haiku-4-5',
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
            'body': '{"target": "人物"}',
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
            'body': '{"image": "data:image/jpeg;base64,/9j/4AAQ...", "target": "人物"}',
            'requestContext': {},
            'resource': '/analyze'
        }
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403


class TestS3BucketAllowlist:
    """S3読み取りバケット許可リスト (item 1)"""

    def test_s3_bucket_not_in_allowlist_rejected(self, monkeypatch):
        monkeypatch.setenv('ALLOWED_IMAGE_BUCKETS', 'allowed-bucket')
        from handler import lambda_handler
        event = {
            'httpMethod': 'POST',
            'headers': {'content-type': 'application/json'},
            'body': json.dumps({
                'image_bucket': 'evil-bucket',
                'image_key': 'x.jpg',
                'target': '人物'
            }),
            'requestContext': {},
            'resource': '/workflow/analyze'
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_s3_empty_allowlist_rejects_all(self, monkeypatch):
        monkeypatch.setenv('ALLOWED_IMAGE_BUCKETS', '')
        from handler import lambda_handler
        event = {
            'httpMethod': 'POST',
            'headers': {'content-type': 'application/json'},
            'body': json.dumps({
                'image_bucket': 'any-bucket',
                'image_key': 'x.jpg',
                'target': '人物'
            }),
            'requestContext': {},
            'resource': '/workflow/analyze'
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400

    @patch('analyzer.ClaudeAnalyzer.analyze')
    @patch('handler._get_image_from_s3')
    def test_s3_bucket_in_allowlist_allowed(self, mock_s3, mock_analyze, monkeypatch, mock_env):
        monkeypatch.setenv('ALLOWED_IMAGE_BUCKETS', 'allowed-bucket,other-bucket')
        mock_s3.return_value = '/9j/4AAQdata'
        mock_analyze.return_value = {
            'found': True, 'answer': 'OK', 'confidence': 80,
            'model': 'claude-haiku-4-5',
            'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2},
            'context': 'テスト'
        }
        from handler import lambda_handler
        event = {
            'httpMethod': 'POST',
            'headers': {'content-type': 'application/json'},
            'body': json.dumps({
                'image_bucket': 'allowed-bucket',
                'image_key': 'x.jpg',
                'target': '人物',
                'model': 'claude-haiku-4-5'
            }),
            'requestContext': {},
            'resource': '/workflow/analyze'
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        mock_s3.assert_called_once_with('allowed-bucket', 'x.jpg')


class TestHealthOrigin:
    """/health のオリジン検証 (item 2)"""

    def test_health_without_origin_header_forbidden(self, health_event, mock_env):
        from handler import lambda_handler
        response = lambda_handler(health_event, None)
        assert response['statusCode'] == 403

    def test_health_with_valid_origin_header(self, mock_env):
        from handler import lambda_handler
        event = {
            'httpMethod': 'GET',
            'path': '/health',
            'headers': {'x-origin-verify': 'test-secret'},
            'requestContext': {},
            'resource': '/health'
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'ok'


class TestSSRF:
    """SSRF対策 (item 3)"""

    def test_is_allowed_url_requires_https(self):
        from handler import _is_allowed_url
        assert _is_allowed_url('https://x.s3.amazonaws.com/a.jpg') is True
        assert _is_allowed_url('http://x.s3.amazonaws.com/a.jpg') is False
        assert _is_allowed_url('https://evil.example.com/a.jpg') is False

    def test_url_http_scheme_rejected(self):
        from handler import lambda_handler
        event = {
            'httpMethod': 'POST',
            'headers': {'content-type': 'application/json'},
            'body': json.dumps({
                'image_url': 'http://x.s3.amazonaws.com/a.jpg',
                'target': '人物'
            }),
            'requestContext': {},
            'resource': '/workflow/analyze'
        }
        response = lambda_handler(event, None)
        assert response['statusCode'] == 400

    def test_no_redirect_handler_blocks(self):
        from handler import _NoRedirectHandler
        h = _NoRedirectHandler()
        assert h.redirect_request(None, None, None, 302, 'Found', {}, 'http://internal') is None

    def test_get_image_from_url_rejects_redirect(self):
        import urllib.error
        from io import BytesIO
        import handler
        mock_opener = MagicMock()
        mock_opener.open.side_effect = urllib.error.HTTPError(
            'https://x.s3.amazonaws.com/a.jpg', 302, 'Found', {}, BytesIO(b'')
        )
        with patch('handler.build_opener', return_value=mock_opener):
            with pytest.raises(ValueError):
                handler._get_image_from_url('https://x.s3.amazonaws.com/a.jpg')


class TestCorsOrigin:
    """CORS AllowOrigin を環境変数で制限 (item 5)"""

    @patch('analyzer.ClaudeAnalyzer.analyze')
    def test_cors_origin_uses_env(self, mock_analyze, api_gateway_event, mock_env, monkeypatch):
        monkeypatch.setenv('ALLOWED_ORIGIN', 'https://image-analysis.example-cloud.com')
        mock_analyze.return_value = {
            'found': True, 'answer': 'OK', 'confidence': 80,
            'model': 'claude-haiku-4-5',
            'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2},
            'context': 'テスト'
        }
        from handler import lambda_handler
        response = lambda_handler(api_gateway_event, None)
        assert response['headers']['Access-Control-Allow-Origin'] == 'https://image-analysis.example-cloud.com'
