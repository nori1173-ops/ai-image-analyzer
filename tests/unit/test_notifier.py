import email
import json
import urllib.error
from email.header import decode_header
from unittest.mock import patch, MagicMock
import pytest


def _decode_subject(raw_subject):
    decoded = ''
    for text, charset in decode_header(raw_subject):
        if isinstance(text, bytes):
            decoded += text.decode(charset or 'utf-8')
        else:
            decoded += text
    return decoded


class TestGetNotifier:
    """環境変数からのSESNotifier構築"""

    @patch('notifier.boto3')
    def test_builds_ses_notifier_from_env(self, mock_boto3, monkeypatch):
        monkeypatch.setenv('SES_SENDER', 'noreply@example.com')
        monkeypatch.setenv('NOTIFY_RECIPIENTS', 'devA@example.co.jp')
        from notifier import get_notifier, SESNotifier

        notifier = get_notifier()

        assert isinstance(notifier, SESNotifier)
        assert notifier.sender == 'noreply@example.com'
        assert notifier.recipients == ['devA@example.co.jp']

    @patch('notifier.boto3')
    def test_multiple_recipients_are_split(self, mock_boto3, monkeypatch):
        monkeypatch.setenv('SES_SENDER', 'noreply@example.com')
        monkeypatch.setenv('NOTIFY_RECIPIENTS', 'a@example.com, b@example.com ,c@example.com')
        from notifier import get_notifier

        notifier = get_notifier()

        assert notifier.recipients == ['a@example.com', 'b@example.com', 'c@example.com']

    def test_missing_sender_raises_value_error(self, monkeypatch):
        monkeypatch.delenv('SES_SENDER', raising=False)
        monkeypatch.setenv('NOTIFY_RECIPIENTS', 'devA@example.co.jp')
        from notifier import get_notifier

        with pytest.raises(ValueError):
            get_notifier()

    def test_missing_recipients_raises_value_error(self, monkeypatch):
        monkeypatch.setenv('SES_SENDER', 'noreply@example.com')
        monkeypatch.delenv('NOTIFY_RECIPIENTS', raising=False)
        from notifier import get_notifier

        with pytest.raises(ValueError):
            get_notifier()


class TestSESNotifierSend:
    """SESNotifier.send のRawMessage構築とSES呼び出し"""

    def _attachments(self):
        return [
            {'filename': 'current.jpg', 'data': b'\xff\xd8\xff\xe0JPEGDATA', 'content_type': 'image/jpeg'},
            {'filename': 'reference.png', 'data': b'\x89PNG\r\n\x1a\nPNGDATA', 'content_type': 'image/png'},
        ]

    @patch('notifier.boto3')
    def test_send_returns_message_id_and_recipients(self, mock_boto3):
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.send_raw_email.return_value = {'MessageId': 'msg-123'}
        from notifier import SESNotifier

        notifier = SESNotifier(sender='noreply@example.com', recipients=['a@example.com', 'b@example.com'])
        result = notifier.send('件名', '本文', [])

        assert result == {'message_id': 'msg-123', 'recipients': ['a@example.com', 'b@example.com']}
        kwargs = mock_client.send_raw_email.call_args.kwargs
        assert kwargs['Source'] == 'noreply@example.com'
        assert kwargs['Destinations'] == ['a@example.com', 'b@example.com']

    @patch('notifier.boto3')
    def test_send_builds_multipart_with_body_and_attachments(self, mock_boto3):
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.send_raw_email.return_value = {'MessageId': 'msg-xyz'}
        from notifier import SESNotifier

        attachments = self._attachments()
        notifier = SESNotifier(sender='noreply@example.com', recipients=['devA@example.co.jp'])
        notifier.send('人物検出通知', '画像に人物が検出されました。', attachments)

        raw = mock_client.send_raw_email.call_args.kwargs['RawMessage']['Data']
        msg = email.message_from_bytes(raw) if isinstance(raw, bytes) else email.message_from_string(raw)

        assert msg['From'] == 'noreply@example.com'
        assert msg['To'] == 'devA@example.co.jp'
        assert _decode_subject(msg['Subject']) == '人物検出通知'

        text_parts = [p for p in msg.walk() if p.get_content_type() == 'text/plain']
        assert len(text_parts) == 1
        assert text_parts[0].get_payload(decode=True).decode('utf-8') == '画像に人物が検出されました。'

        att_parts = [p for p in msg.walk() if p.get_content_disposition() == 'attachment']
        assert len(att_parts) == 2
        by_name = {p.get_filename(): p for p in att_parts}
        assert by_name['current.jpg'].get_content_type() == 'image/jpeg'
        assert by_name['current.jpg'].get_payload(decode=True) == attachments[0]['data']
        assert by_name['reference.png'].get_content_type() == 'image/png'
        assert by_name['reference.png'].get_payload(decode=True) == attachments[1]['data']

    @patch('notifier.boto3')
    def test_send_without_attachments(self, mock_boto3):
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.send_raw_email.return_value = {'MessageId': 'msg-noatt'}
        from notifier import SESNotifier

        notifier = SESNotifier(sender='noreply@example.com', recipients=['devA@example.co.jp'])
        result = notifier.send('件名のみ', '添付なし本文')

        assert result['message_id'] == 'msg-noatt'
        raw = mock_client.send_raw_email.call_args.kwargs['RawMessage']['Data']
        msg = email.message_from_bytes(raw) if isinstance(raw, bytes) else email.message_from_string(raw)
        att_parts = [p for p in msg.walk() if p.get_content_disposition() == 'attachment']
        assert att_parts == []

    @patch('notifier.boto3')
    def test_send_with_to_cc_bcc(self, mock_boto3):
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.send_raw_email.return_value = {'MessageId': 'msg-custom'}
        from notifier import SESNotifier

        notifier = SESNotifier(sender='noreply@example.com', recipients=['default@example.com'])
        result = notifier.send(
            '宛先指定',
            '本文',
            to=['to@example.com'],
            cc=['cc@example.com'],
            bcc=['bcc@example.com'],
        )

        kwargs = mock_client.send_raw_email.call_args.kwargs
        raw = kwargs['RawMessage']['Data']
        msg = email.message_from_bytes(raw) if isinstance(raw, bytes) else email.message_from_string(raw)
        assert msg['To'] == 'to@example.com'
        assert msg['Cc'] == 'cc@example.com'
        assert msg['Bcc'] is None
        assert kwargs['Destinations'] == ['to@example.com', 'cc@example.com', 'bcc@example.com']
        assert result['message_id'] == 'msg-custom'
        assert result['recipients'] == ['to@example.com', 'cc@example.com', 'bcc@example.com']


class TestLINENotifier:
    """LINE Messaging API push message の構築"""

    @patch('notifier.urllib.request.urlopen')
    def test_send_line_posts_text_and_images(self, mock_urlopen):
        response = MagicMock()
        response.getcode.return_value = 200
        response.read.return_value = b'{}'
        mock_urlopen.return_value.__enter__.return_value = response
        from notifier import LINENotifier

        notifier = LINENotifier('secret-token', 'U123456')
        notifier.send_line(
            '危険を検知しました',
            ['https://example.com/before.jpg', 'https://example.com/after.jpg'],
        )

        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode('utf-8'))
        assert payload == {
            'to': 'U123456',
            'messages': [
                {'type': 'text', 'text': '危険を検知しました'},
                {
                    'type': 'image',
                    'originalContentUrl': 'https://example.com/before.jpg',
                    'previewImageUrl': 'https://example.com/before.jpg',
                },
                {
                    'type': 'image',
                    'originalContentUrl': 'https://example.com/after.jpg',
                    'previewImageUrl': 'https://example.com/after.jpg',
                },
            ],
        }
        assert request.get_header('Authorization') == 'Bearer secret-token'
        assert mock_urlopen.call_args.kwargs['timeout'] == 10

    @patch('notifier.urllib.request.urlopen')
    def test_send_line_raises_on_non_2xx_without_exposing_token(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='https://api.line.me/v2/bot/message/push',
            code=500,
            msg='Internal Server Error',
            hdrs=None,
            fp=None,
        )
        from notifier import LINENotifier

        notifier = LINENotifier('secret-token', 'U123456')

        with pytest.raises(RuntimeError) as exc_info:
            notifier.send_line('危険を検知しました', [])

        assert '500' in str(exc_info.value)
        assert 'secret-token' not in str(exc_info.value)

    @patch('notifier.urllib.request.urlopen')
    def test_send_line_truncates_text_to_4900_characters(self, mock_urlopen):
        response = MagicMock()
        response.getcode.return_value = 200
        response.read.return_value = b'{}'
        mock_urlopen.return_value.__enter__.return_value = response
        from notifier import LINENotifier

        text = '危' * 5000
        LINENotifier('secret-token', 'U123456').send_line(text, [])

        request = mock_urlopen.call_args.args[0]
        sent_text = json.loads(request.data.decode('utf-8'))['messages'][0]['text']
        assert len(sent_text) == 4900
        assert sent_text == f'{text[:4899]}…'


class TestGetLineNotifier:
    """LINE通知設定の取得"""

    @patch('notifier.boto3')
    def test_missing_notify_to_raises_not_configured(self, mock_boto3, monkeypatch):
        monkeypatch.delenv('LINE_NOTIFY_TO', raising=False)
        from notifier import LineNotConfiguredError, get_line_notifier

        with pytest.raises(LineNotConfiguredError) as exc_info:
            get_line_notifier()

        assert 'LINE_NOTIFY_TO' in str(exc_info.value)
        mock_boto3.client.assert_not_called()

    @patch('notifier.boto3')
    def test_gets_token_from_ssm(self, mock_boto3, monkeypatch):
        monkeypatch.setenv('LINE_NOTIFY_TO', 'U123456')
        monkeypatch.setenv('LINE_TOKEN_PARAM', '/custom/line-token')
        mock_ssm = MagicMock()
        mock_ssm.get_parameter.return_value = {
            'Parameter': {'Value': 'channel-access-token'}
        }
        mock_boto3.client.return_value = mock_ssm
        from notifier import LINENotifier, get_line_notifier

        line_notifier = get_line_notifier()

        assert isinstance(line_notifier, LINENotifier)
        assert line_notifier.to == 'U123456'
        assert line_notifier.channel_access_token == 'channel-access-token'
        mock_ssm.get_parameter.assert_called_once_with(
            Name='/custom/line-token', WithDecryption=True)

    @patch('notifier.boto3')
    def test_parameter_not_found_raises_not_configured(self, mock_boto3, monkeypatch):
        monkeypatch.setenv('LINE_NOTIFY_TO', 'U123456')
        parameter_not_found = type('ParameterNotFound', (Exception,), {})
        mock_ssm = MagicMock()
        mock_ssm.exceptions.ParameterNotFound = parameter_not_found
        mock_ssm.get_parameter.side_effect = parameter_not_found()
        mock_boto3.client.return_value = mock_ssm
        from notifier import LineNotConfiguredError, get_line_notifier

        with pytest.raises(LineNotConfiguredError) as exc_info:
            get_line_notifier()

        assert 'LINEアクセストークン' in str(exc_info.value)

    @patch('notifier.boto3')
    def test_reuses_cached_token_without_calling_ssm_again(self, mock_boto3, monkeypatch):
        monkeypatch.setenv('LINE_NOTIFY_TO', 'U123456')
        mock_ssm = MagicMock()
        mock_ssm.get_parameter.return_value = {
            'Parameter': {'Value': 'cached-token'}
        }
        mock_boto3.client.return_value = mock_ssm
        from notifier import get_line_notifier

        first = get_line_notifier()
        second = get_line_notifier()

        assert first.channel_access_token == 'cached-token'
        assert second.channel_access_token == 'cached-token'
        mock_boto3.client.assert_called_once_with('ssm')
        mock_ssm.get_parameter.assert_called_once()
