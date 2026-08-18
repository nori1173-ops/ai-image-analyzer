import json
import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lambda'))

_mock_logger_instance = MagicMock()

_mock_lambda_logger_class = MagicMock()
_mock_lambda_logger_class.return_value = _mock_logger_instance
_mock_lambda_logger_class.contextualize = lambda f: f

_mock_logging_module = MagicMock()
_mock_logging_module.LambdaLogger = _mock_lambda_logger_class

_mock_example_powertools = MagicMock()
_mock_example_powertools.logging = _mock_logging_module

sys.modules['example_powertools'] = _mock_example_powertools
sys.modules['example_powertools.logging'] = _mock_logging_module


@pytest.fixture
def mock_logger():
    _mock_logger_instance.reset_mock()
    return _mock_logger_instance


@pytest.fixture(autouse=True)
def reset_line_token_cache(monkeypatch):
    import notifier
    monkeypatch.setattr(notifier, '_cached_line_token', None)


@pytest.fixture
def api_gateway_event():
    """POST /analyze のイベント"""
    return {
        'httpMethod': 'POST',
        'path': '/analyze',
        'headers': {
            'content-type': 'application/json',
            'x-origin-verify': 'test-secret'
        },
        'body': '{"image": "data:image/jpeg;base64,/9j/4AAQ...", "target": "人物", "model": "claude-haiku-4-5", "detail": "low"}',
        'requestContext': {'authorizer': {'claims': {'sub': 'test-user'}}},
        'resource': '/analyze'
    }


@pytest.fixture
def workflow_event():
    """POST /workflow/analyze のイベント"""
    return {
        'httpMethod': 'POST',
        'path': '/workflow/analyze',
        'headers': {'content-type': 'application/json'},
        'body': '{"data": "/9j/4AAQ...", "filename": "photo.jpg", "target": "人物", "model": "claude-haiku-4-5"}',
        'requestContext': {},
        'resource': '/workflow/analyze'
    }


@pytest.fixture
def health_event():
    """GET /health のイベント"""
    return {
        'httpMethod': 'GET',
        'path': '/health',
        'headers': {},
        'requestContext': {},
        'resource': '/health'
    }


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv('ORIGIN_VERIFY_HEADER', 'x-origin-verify')
    monkeypatch.setenv('ORIGIN_VERIFY_VALUE', 'test-secret')
    monkeypatch.setenv('ALLOWED_IMAGE_BUCKETS', 'test-bucket')
    monkeypatch.setenv('ANTHROPIC_AWS_WORKSPACE_ID', 'ws-test-dummy')
    monkeypatch.setenv('AWS_REGION', 'ap-northeast-1')
    monkeypatch.setenv('BEDROCK_JP_REGION', 'ap-northeast-1')
    monkeypatch.setenv('BEDROCK_US_REGION', 'us-east-1')
    monkeypatch.setenv('BEDROCK_GPT_REGION', 'us-east-2')
    monkeypatch.setenv('DEFAULT_MODEL', 'claude-haiku-4-5')
    monkeypatch.setenv('SES_SENDER', 'noreply@image-analysis.example-cloud.com')
    monkeypatch.setenv('NOTIFY_RECIPIENTS', 'devA@example.co.jp')
    monkeypatch.setenv('LINE_IMAGES_BUCKET', 'line-images-bucket')
    monkeypatch.delenv('LINE_NOTIFY_TO', raising=False)


@pytest.fixture
def s3_event():
    """S3キー参照のイベント"""
    return {
        'httpMethod': 'POST',
        'path': '/workflow/analyze',
        'headers': {'content-type': 'application/json'},
        'body': json.dumps({
            'image_bucket': 'test-bucket',
            'image_key': 'tmp/photo.jpg',
            'target': '人物',
            'model': 'claude-haiku-4-5'
        }),
        'requestContext': {},
        'resource': '/workflow/analyze'
    }


@pytest.fixture
def url_event():
    """URL参照のイベント"""
    return {
        'httpMethod': 'POST',
        'path': '/workflow/analyze',
        'headers': {'content-type': 'application/json'},
        'body': json.dumps({
            'image_url': 'https://test-bucket.s3.ap-northeast-1.amazonaws.com/photo.jpg',
            'target': '人物',
            'model': 'claude-haiku-4-5'
        }),
        'requestContext': {},
        'resource': '/workflow/analyze'
    }
