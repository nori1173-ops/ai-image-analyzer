import json
import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lambda'))

_mock_logger_instance = MagicMock()
_mock_logger_instance.inject_lambda_context = lambda f: f

_mock_powertools = MagicMock()
_mock_powertools.Logger = MagicMock(return_value=_mock_logger_instance)

sys.modules['aws_lambda_powertools'] = _mock_powertools


@pytest.fixture
def mock_logger():
    _mock_logger_instance.reset_mock()
    return _mock_logger_instance


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
        'body': '{"image": "data:image/jpeg;base64,/9j/4AAQ...", "target": "crack", "model": "gpt-4.1-mini", "detail": "low"}',
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
        'body': '{"data": "/9j/4AAQ...", "filename": "photo.jpg", "target": "crack"}',
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
    monkeypatch.setenv('SSM_OPENAI_API_KEY_PATH', '/image-analysis/openai-api-key')


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
            'target': 'crack'
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
            'target': 'crack'
        }),
        'requestContext': {},
        'resource': '/workflow/analyze'
    }
