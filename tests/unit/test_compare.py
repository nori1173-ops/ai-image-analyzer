import base64
import json
from unittest.mock import patch, MagicMock
import pytest


class TestClaudeAnalyzerCompare:
    """ClaudeAnalyzer.compare (tool_use強制 report_comparison)"""

    def _build_response(self, danger=True, risk_level='high',
                        reason='斜面上部で新たな亀裂と土砂の流出が確認できます',
                        changes='前回になかった崩落跡が今回画像の中央に出現'):
        tool_block = MagicMock()
        tool_block.type = 'tool_use'
        tool_block.name = 'report_comparison'
        tool_block.input = {
            'danger': danger,
            'risk_level': risk_level,
            'reason': reason,
            'changes': changes,
        }
        response = MagicMock()
        response.content = [tool_block]
        response.model = 'claude-sonnet-5'
        response.usage.input_tokens = 2000
        response.usage.output_tokens = 60
        return response

    @patch('analyzer.AnthropicAWS')
    def test_compare_returns_expected_format(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._build_response()

        from analyzer import ClaudeAnalyzer

        result = ClaudeAnalyzer().compare('beforedata', 'afterdata', '土砂崩れ', 'claude-sonnet-5', 'low')

        assert result['danger'] is True
        assert result['risk_level'] == 'high'
        assert result['reason'] == '斜面上部で新たな亀裂と土砂の流出が確認できます'
        assert result['changes'] == '前回になかった崩落跡が今回画像の中央に出現'
        assert result['model'] == 'claude-sonnet-5'
        assert result['usage'] == {
            'prompt_tokens': 2000,
            'completion_tokens': 60,
            'total_tokens': 2060,
        }

    @patch('analyzer.AnthropicAWS')
    def test_compare_forces_tool_use_and_sends_two_images(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._build_response()

        from analyzer import ClaudeAnalyzer

        ClaudeAnalyzer().compare('beforedata', 'afterdata', '河川水位', 'claude-sonnet-5', 'low')

        kwargs = mock_client.messages.create.call_args.kwargs
        assert kwargs['model'] == 'claude-sonnet-5'
        assert kwargs['max_tokens'] == 1000
        assert kwargs['tool_choice'] == {'type': 'tool', 'name': 'report_comparison'}
        assert kwargs['tools'][0]['name'] == 'report_comparison'
        schema = kwargs['tools'][0]['input_schema']
        assert schema['properties']['risk_level']['enum'] == ['none', 'low', 'medium', 'high']
        assert set(schema['required']) == {'danger', 'risk_level', 'reason', 'changes'}

        content = kwargs['messages'][0]['content']
        image_blocks = [b for b in content if b['type'] == 'image']
        assert len(image_blocks) == 2
        assert image_blocks[0]['source']['data'] == 'beforedata'
        assert image_blocks[1]['source']['data'] == 'afterdata'
        text_blocks = [b['text'] for b in content if b['type'] == 'text']
        assert any('河川水位' in t for t in text_blocks)

    @patch('analyzer.AnthropicAWS')
    def test_compare_detects_media_type_per_image(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._build_response()

        from analyzer import ClaudeAnalyzer

        ClaudeAnalyzer().compare('/9j/4AAQjpeg', 'iVBORw0KGgopng', '土砂崩れ', 'claude-sonnet-5', 'low')

        kwargs = mock_client.messages.create.call_args.kwargs
        image_blocks = [b for b in kwargs['messages'][0]['content'] if b['type'] == 'image']
        assert image_blocks[0]['source']['media_type'] == 'image/jpeg'
        assert image_blocks[1]['source']['media_type'] == 'image/png'

    @patch('analyzer.AnthropicAWS')
    def test_compare_passes_effort_output_config(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._build_response()

        from analyzer import ClaudeAnalyzer

        ClaudeAnalyzer().compare('beforedata', 'afterdata', '土砂崩れ', 'claude-sonnet-5', 'low', effort='medium')

        kwargs = mock_client.messages.create.call_args.kwargs
        assert kwargs['output_config'] == {'effort': 'medium'}

    @patch('analyzer.AnthropicAWS')
    def test_compare_omits_output_config_without_effort(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = self._build_response()

        from analyzer import ClaudeAnalyzer

        ClaudeAnalyzer().compare('beforedata', 'afterdata', '土砂崩れ', 'claude-sonnet-5', 'low')

        kwargs = mock_client.messages.create.call_args.kwargs
        assert 'output_config' not in kwargs

    @patch('analyzer.AnthropicAWS')
    def test_compare_raises_without_tool_use(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        text_block = MagicMock()
        text_block.type = 'text'
        response = MagicMock()
        response.content = [text_block]
        mock_client.messages.create.return_value = response

        from analyzer import ClaudeAnalyzer

        with pytest.raises(ValueError):
            ClaudeAnalyzer().compare('b', 'a', '土砂崩れ', 'claude-sonnet-5', 'low')


class TestExtractBase64ImagePrefix:
    """prefix対応版 extract_base64_image"""

    def test_before_data_raw(self):
        from handler import extract_base64_image
        img, err = extract_base64_image({'before_data': 'RAWBASE64'}, 'before_')
        assert img == 'RAWBASE64'
        assert err is None

    def test_before_image_data_uri(self):
        from handler import extract_base64_image
        img, err = extract_base64_image(
            {'before_image': 'data:image/png;base64,ABCDEF'}, 'before_')
        assert img == 'ABCDEF'
        assert err is None

    def test_after_data_raw(self):
        from handler import extract_base64_image
        img, err = extract_base64_image({'after_data': 'AFTERRAW'}, 'after_')
        assert img == 'AFTERRAW'
        assert err is None

    @patch('handler._get_image_from_url')
    def test_before_image_url_allowed(self, mock_url):
        mock_url.return_value = 'URLBASE64'
        from handler import extract_base64_image
        img, err = extract_base64_image(
            {'before_image_url': 'https://test-bucket.s3.ap-northeast-1.amazonaws.com/before.jpg'},
            'before_')
        assert img == 'URLBASE64'
        assert err is None

    @patch('handler._get_image_from_s3')
    def test_before_bucket_allowed(self, mock_s3, mock_env):
        mock_s3.return_value = 'S3BASE64'
        from handler import extract_base64_image
        img, err = extract_base64_image(
            {'before_image_bucket': 'test-bucket', 'before_image_key': 'before.jpg'},
            'before_')
        assert img == 'S3BASE64'
        assert err is None
        mock_s3.assert_called_once_with('test-bucket', 'before.jpg')

    def test_before_bucket_not_allowed_raises(self, mock_env):
        from handler import extract_base64_image
        with pytest.raises(ValueError):
            extract_base64_image(
                {'before_image_bucket': 'evil-bucket', 'before_image_key': 'before.jpg'},
                'before_')

    def test_missing_returns_error(self):
        from handler import extract_base64_image
        img, err = extract_base64_image({}, 'before_')
        assert img is None
        assert 'before_' in err

    def test_default_prefix_backward_compatible(self):
        from handler import extract_base64_image
        img, err = extract_base64_image({'data': 'LEGACY'})
        assert img == 'LEGACY'
        assert err is None


def _compare_result(danger=True):
    return {
        'danger': danger,
        'risk_level': 'high' if danger else 'none',
        'reason': '斜面が崩落しています' if danger else '災害と無関係な変化のみ',
        'changes': '崩落跡を検出' if danger else '落ち葉と影の移動のみ',
        'model': 'claude-haiku-4-5',
        'usage': {'prompt_tokens': 300, 'completion_tokens': 40, 'total_tokens': 340},
    }


def _compare_event(resource='/compare', origin=True, **body_overrides):
    body = {
        'before_data': '/9j/4AAQ',
        'after_data': '/9j/4BBQ',
        'perspective': '土砂崩れ',
        'model': 'claude-haiku-4-5',
    }
    body.update(body_overrides)
    headers = {'content-type': 'application/json'}
    if origin:
        headers['x-origin-verify'] = 'test-secret'
    return {
        'httpMethod': 'POST',
        'headers': headers,
        'body': json.dumps(body),
        'requestContext': {},
        'resource': resource,
    }


class TestCompareHandler:
    """POST /compare, /workflow/compare"""

    @patch('handler._resolve_analyzer')
    def test_omitted_model_uses_bedrock_sonnet_code_fallback(
            self, mock_resolve, mock_env, monkeypatch):
        monkeypatch.delenv('DEFAULT_MODEL', raising=False)
        mock_resolve.return_value.compare.return_value = _compare_result(False)
        from handler import lambda_handler

        event = _compare_event()
        body = json.loads(event['body'])
        del body['model']
        event['body'] = json.dumps(body)

        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        mock_resolve.assert_called_once_with('anthropic.claude-sonnet-5')
        assert mock_resolve.return_value.compare.call_args.args[3] == (
            'anthropic.claude-sonnet-5')

    @patch('analyzer.ClaudeAnalyzer.compare')
    def test_compare_success(self, mock_compare, mock_env):
        mock_compare.return_value = _compare_result(danger=True)
        from handler import lambda_handler

        response = lambda_handler(_compare_event(), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['danger'] is True
        assert body['risk_level'] == 'high'
        assert 'reason' in body
        assert 'changes' in body
        assert 'usage' in body
        assert 'elapsed_seconds' in body
        assert body['notified'] is False
        assert 'message_id' not in body

    @patch('analyzer.ClaudeAnalyzer.compare')
    @patch('analyzer.AnthropicAWS')
    def test_compare_effort_passed_to_analyzer(self, mock_anthropic, mock_compare, mock_env):
        mock_compare.return_value = _compare_result(danger=False)
        from handler import lambda_handler

        event = _compare_event(model='claude-sonnet-5', effort='low')
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        assert mock_compare.call_args.kwargs['effort'] == 'low'

    def test_compare_invalid_effort_400(self, mock_env):
        from handler import lambda_handler

        response = lambda_handler(_compare_event(effort='ultra'), None)

        assert response['statusCode'] == 400
        assert 'effort' in json.loads(response['body'])['error'].lower()

    @patch('handler._resolve_analyzer')
    def test_compare_gpt_model_400(self, mock_resolve, mock_env):
        mock_resolve.return_value.compare.return_value = _compare_result(danger=False)
        from handler import lambda_handler

        response = lambda_handler(_compare_event(model='gpt-4.1-mini'), None)

        assert response['statusCode'] == 400
        assert json.loads(response['body']) == {'error': 'Invalid model'}
        mock_resolve.assert_not_called()

    @pytest.mark.parametrize(('field', 'value'), [
        ('notify_to', ['invalid-address']),
        ('notify_cc', ['user@example.com'] * 11),
        ('notify_bcc', 'user@example.com'),
        ('notify_to', [123]),
    ])
    def test_compare_invalid_notify_recipients_400(
            self, field, value, mock_env):
        from handler import lambda_handler

        response = lambda_handler(_compare_event(**{field: value}), None)

        assert response['statusCode'] == 400
        assert json.loads(response['body']) == {'error': f'Invalid {field}'}

    def test_compare_missing_before_400(self, mock_env):
        from handler import lambda_handler
        event = _compare_event()
        body = json.loads(event['body'])
        del body['before_data']
        event['body'] = json.dumps(body)

        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        assert 'before' in json.loads(response['body'])['error']

    def test_compare_missing_after_400(self, mock_env):
        from handler import lambda_handler
        event = _compare_event()
        body = json.loads(event['body'])
        del body['after_data']
        event['body'] = json.dumps(body)

        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        assert 'after' in json.loads(response['body'])['error']

    def test_compare_missing_perspective_400(self, mock_env):
        from handler import lambda_handler
        event = _compare_event()
        body = json.loads(event['body'])
        del body['perspective']
        event['body'] = json.dumps(body)

        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        assert 'perspective' in json.loads(response['body'])['error']

    def test_compare_origin_verification_403(self, mock_env):
        from handler import lambda_handler
        response = lambda_handler(_compare_event(origin=False), None)
        assert response['statusCode'] == 403

    @patch('notifier.get_notifier')
    @patch('analyzer.ClaudeAnalyzer.compare')
    def test_compare_notify_danger_sends(self, mock_compare, mock_get_notifier, mock_env):
        mock_compare.return_value = _compare_result(danger=True)
        mock_notifier = MagicMock()
        mock_notifier.send.return_value = {'message_id': 'msg-danger', 'recipients': ['devA@example.co.jp']}
        mock_get_notifier.return_value = mock_notifier
        from handler import lambda_handler

        response = lambda_handler(_compare_event(notify=True), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['notified'] is True
        assert body['message_id'] == 'msg-danger'

        mock_notifier.send.assert_called_once()
        args, kwargs = mock_notifier.send.call_args
        subject = args[0]
        attachments = args[2]
        assert '土砂崩れ' in subject
        assert len(attachments) == 2
        assert {a['filename'] for a in attachments} == {'before.jpg', 'after.jpg'}

    @patch('notifier.get_notifier')
    @patch('analyzer.ClaudeAnalyzer.compare')
    def test_compare_passes_to_cc_bcc_to_notifier(
            self, mock_compare, mock_get_notifier, mock_env):
        mock_compare.return_value = _compare_result(danger=True)
        mock_notifier = MagicMock()
        mock_notifier.send.return_value = {
            'message_id': 'msg-custom',
            'recipients': ['to@example.com', 'cc@example.com', 'bcc@example.com'],
        }
        mock_get_notifier.return_value = mock_notifier
        from handler import lambda_handler

        response = lambda_handler(_compare_event(
            notify=True,
            notify_to=['to@example.com'],
            notify_cc=['cc@example.com'],
            notify_bcc=['bcc@example.com'],
        ), None)

        assert response['statusCode'] == 200
        assert mock_notifier.send.call_args.kwargs == {
            'to': ['to@example.com'],
            'cc': ['cc@example.com'],
            'bcc': ['bcc@example.com'],
        }

    @patch('notifier.get_notifier')
    @patch('analyzer.ClaudeAnalyzer.compare')
    def test_compare_empty_notify_to_uses_default_recipients(
            self, mock_compare, mock_get_notifier, mock_env):
        mock_compare.return_value = _compare_result(danger=True)
        mock_notifier = MagicMock()
        mock_notifier.send.return_value = {
            'message_id': 'msg-default',
            'recipients': ['devA@example.co.jp'],
        }
        mock_get_notifier.return_value = mock_notifier
        from handler import lambda_handler

        response = lambda_handler(_compare_event(notify=True, notify_to=[]), None)

        assert response['statusCode'] == 200
        assert mock_notifier.send.call_args.kwargs['to'] is None

    @patch('notifier.get_notifier')
    @patch('analyzer.ClaudeAnalyzer.compare')
    def test_compare_notify_png_attachment_extension(self, mock_compare, mock_get_notifier, mock_env):
        mock_compare.return_value = _compare_result(danger=True)
        mock_notifier = MagicMock()
        mock_notifier.send.return_value = {'message_id': 'msg-png', 'recipients': ['devA@example.co.jp']}
        mock_get_notifier.return_value = mock_notifier
        from handler import lambda_handler

        event = _compare_event(
            notify=True,
            before_data='iVBORw0KGgoAAAANSUhEUg==',
            after_data='iVBORw0KGgoAAAANSUhEUh==',
        )
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        attachments = mock_notifier.send.call_args.args[2]
        assert {a['filename'] for a in attachments} == {'before.png', 'after.png'}
        assert {a['content_type'] for a in attachments} == {'image/png'}

    @patch('notifier.get_notifier')
    @patch('analyzer.ClaudeAnalyzer.compare')
    def test_compare_notify_no_danger_no_send(self, mock_compare, mock_get_notifier, mock_env):
        mock_compare.return_value = _compare_result(danger=False)
        mock_notifier = MagicMock()
        mock_get_notifier.return_value = mock_notifier
        from handler import lambda_handler

        response = lambda_handler(_compare_event(notify=True), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['danger'] is False
        assert body['notified'] is False
        mock_notifier.send.assert_not_called()

    @patch('notifier.get_notifier')
    @patch('analyzer.ClaudeAnalyzer.compare')
    def test_compare_notify_false_no_send(self, mock_compare, mock_get_notifier, mock_env):
        mock_compare.return_value = _compare_result(danger=True)
        mock_notifier = MagicMock()
        mock_get_notifier.return_value = mock_notifier
        from handler import lambda_handler

        response = lambda_handler(_compare_event(notify=False), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['notified'] is False
        mock_notifier.send.assert_not_called()

    @patch('notifier.get_notifier')
    @patch('analyzer.ClaudeAnalyzer.compare')
    def test_compare_notify_failure_still_200(self, mock_compare, mock_get_notifier, mock_env):
        mock_compare.return_value = _compare_result(danger=True)
        mock_notifier = MagicMock()
        mock_notifier.send.side_effect = RuntimeError('SES送信失敗')
        mock_get_notifier.return_value = mock_notifier
        from handler import lambda_handler

        response = lambda_handler(_compare_event(notify=True), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['notified'] is False
        assert 'notify_error' in body
        assert 'message_id' not in body

    @patch('analyzer.ClaudeAnalyzer.compare')
    def test_compare_notify_line_not_configured_is_skipped(
            self, mock_compare, mock_env, mock_logger):
        mock_compare.return_value = _compare_result(danger=True)
        from handler import lambda_handler

        response = lambda_handler(_compare_event(notify_line=True), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['line_notified'] is False
        assert 'LINE_NOTIFY_TO' in body['line_skip_reason']
        mock_logger.warning.assert_called()

    @patch('handler.boto3')
    @patch('notifier.get_line_notifier')
    @patch('analyzer.ClaudeAnalyzer.compare')
    def test_compare_notify_line_success(
            self, mock_compare, mock_get_line_notifier, mock_boto3, mock_env):
        mock_compare.return_value = _compare_result(danger=True)
        mock_line_notifier = MagicMock()
        mock_get_line_notifier.return_value = mock_line_notifier
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.side_effect = [
            'https://example.com/before.jpg?signature=1',
            'https://example.com/after.jpg?signature=2',
        ]
        mock_boto3.client.return_value = mock_s3
        from handler import lambda_handler

        response = lambda_handler(_compare_event(notify_line=True), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['line_notified'] is True
        assert mock_s3.put_object.call_count == 2
        before_put = mock_s3.put_object.call_args_list[0].kwargs
        after_put = mock_s3.put_object.call_args_list[1].kwargs
        assert before_put['Bucket'] == 'line-images-bucket'
        assert before_put['Key'].startswith('line/')
        assert before_put['Key'].endswith('/before.jpg')
        assert after_put['Key'].endswith('/after.jpg')
        assert before_put['Key'].split('/')[1] == after_put['Key'].split('/')[1]
        assert mock_s3.generate_presigned_url.call_count == 2
        for call in mock_s3.generate_presigned_url.call_args_list:
            assert call.args[0] == 'get_object'
            assert call.kwargs['ExpiresIn'] == 21600
        text, image_urls = mock_line_notifier.send_line.call_args.args
        assert '監視観点: 土砂崩れ' in text
        assert '危険度: high' in text
        assert '画像1枚目=前回/2枚目=今回' in text
        assert '画像リンクは6時間で失効' in text
        assert image_urls == [
            'https://example.com/before.jpg?signature=1',
            'https://example.com/after.jpg?signature=2',
        ]

    @patch('handler.boto3')
    @patch('notifier.get_line_notifier')
    def test_line_sends_image_at_preview_size_limit(
            self, mock_get_line_notifier, mock_boto3, mock_env):
        mock_line_notifier = MagicMock()
        mock_get_line_notifier.return_value = mock_line_notifier
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.side_effect = [
            'https://example.com/before.jpg',
            'https://example.com/after.jpg',
        ]
        mock_boto3.client.return_value = mock_s3
        from handler import _send_line_danger_notification

        before = base64.b64encode(b'a' * 1_048_576).decode('ascii')
        after = base64.b64encode(b'after').decode('ascii')
        _send_line_danger_notification(
            '土砂崩れ', _compare_result(), before, after)

        assert mock_s3.put_object.call_count == 2
        assert len(mock_s3.put_object.call_args_list[0].kwargs['Body']) == 1_048_576
        text, image_urls = mock_line_notifier.send_line.call_args.args
        assert 'サイズ超過' not in text
        assert image_urls == [
            'https://example.com/before.jpg',
            'https://example.com/after.jpg',
        ]

    @patch('handler.boto3')
    @patch('notifier.get_line_notifier')
    def test_line_skips_oversized_image_and_adds_note(
            self, mock_get_line_notifier, mock_boto3, mock_env):
        mock_line_notifier = MagicMock()
        mock_get_line_notifier.return_value = mock_line_notifier
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = 'https://example.com/after.jpg'
        mock_boto3.client.return_value = mock_s3
        from handler import _send_line_danger_notification

        before = base64.b64encode(b'a' * 1_048_577).decode('ascii')
        after = base64.b64encode(b'after').decode('ascii')
        _send_line_danger_notification(
            '土砂崩れ', _compare_result(), before, after)

        mock_s3.put_object.assert_called_once()
        assert mock_s3.put_object.call_args.kwargs['Key'].endswith('/after.jpg')
        text, image_urls = mock_line_notifier.send_line.call_args.args
        assert '画像1枚目=今回' in text
        assert '（前回画像はサイズ超過のためLINE送信対象外。メール添付を参照）' in text
        assert image_urls == ['https://example.com/after.jpg']

    @patch('handler.boto3')
    @patch('notifier.get_line_notifier')
    def test_line_sends_text_only_when_both_images_are_oversized(
            self, mock_get_line_notifier, mock_boto3, mock_env):
        mock_line_notifier = MagicMock()
        mock_get_line_notifier.return_value = mock_line_notifier
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        from handler import _send_line_danger_notification

        oversized = base64.b64encode(b'a' * 1_048_577).decode('ascii')
        _send_line_danger_notification(
            '土砂崩れ', _compare_result(), oversized, oversized)

        mock_s3.put_object.assert_not_called()
        mock_s3.generate_presigned_url.assert_not_called()
        text, image_urls = mock_line_notifier.send_line.call_args.args
        assert '（前回画像/今回画像はサイズ超過のためLINE送信対象外。メール添付を参照）' in text
        assert image_urls == []

    @patch('handler.boto3')
    @patch('notifier.get_line_notifier')
    @patch('analyzer.ClaudeAnalyzer.compare')
    def test_compare_notify_line_s3_failure_still_200(
            self, mock_compare, mock_get_line_notifier, mock_boto3,
            mock_env, mock_logger):
        mock_compare.return_value = _compare_result(danger=True)
        mock_get_line_notifier.return_value = MagicMock()
        mock_boto3.client.return_value.put_object.side_effect = RuntimeError('S3 upload failed')
        from handler import lambda_handler

        response = lambda_handler(_compare_event(notify_line=True), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['line_notified'] is False
        assert body['line_error'] == 'S3 upload failed'
        mock_logger.error.assert_called()

    @patch('handler.boto3')
    @patch('notifier.get_line_notifier')
    @patch('analyzer.ClaudeAnalyzer.compare')
    def test_compare_notify_line_false_does_nothing(
            self, mock_compare, mock_get_line_notifier, mock_boto3, mock_env):
        mock_compare.return_value = _compare_result(danger=True)
        from handler import lambda_handler

        response = lambda_handler(_compare_event(notify_line=False), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['line_notified'] is False
        mock_get_line_notifier.assert_not_called()
        mock_boto3.client.assert_not_called()

    @patch('analyzer.ClaudeAnalyzer.compare')
    def test_workflow_compare_no_origin_check(self, mock_compare, mock_env):
        mock_compare.return_value = _compare_result(danger=True)
        from handler import lambda_handler

        response = lambda_handler(_compare_event(resource='/workflow/compare', origin=False), None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['danger'] is True
