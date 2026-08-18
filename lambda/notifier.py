import json
import os
import urllib.error
import urllib.request
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import boto3

_cached_line_token = None
LINE_TEXT_MAX_LENGTH = 4900


class Notifier:
    """通知プロバイダー抽象レイヤー"""
    def send(self, subject: str, body: str, attachments: list[dict] = None,
             to: list[str] = None, cc: list[str] = None,
             bcc: list[str] = None) -> dict:
        raise NotImplementedError


class LineNotifier:
    """LINE通知プロバイダー抽象レイヤー"""
    def send_line(self, text: str, image_urls: list[str]) -> dict:
        raise NotImplementedError


class LineNotConfiguredError(Exception):
    pass


class SESNotifier(Notifier):
    """Amazon SES による通知（send_raw_emailで添付対応）"""
    def __init__(self, sender: str, recipients: list[str]):
        if not sender:
            raise ValueError('SES送信元アドレスが設定されていません (SES_SENDER)')
        if not recipients:
            raise ValueError('通知先が設定されていません (NOTIFY_RECIPIENTS)')
        self.sender = sender
        self.recipients = recipients
        self.client = boto3.client('ses')

    def send(self, subject: str, body: str, attachments: list[dict] = None,
             to: list[str] = None, cc: list[str] = None,
             bcc: list[str] = None) -> dict:
        attachments = attachments or []
        actual_to = self.recipients if to is None else to
        cc = cc or []
        bcc = bcc or []
        destinations = [*actual_to, *cc, *bcc]

        message = MIMEMultipart()
        message['Subject'] = Header(subject, 'utf-8')
        message['From'] = self.sender
        if actual_to:
            message['To'] = ', '.join(actual_to)
        if cc:
            message['Cc'] = ', '.join(cc)
        message.attach(MIMEText(body, 'plain', 'utf-8'))

        for attachment in attachments:
            maintype, _, subtype = attachment['content_type'].partition('/')
            part = MIMEBase(maintype, subtype)
            part.set_payload(attachment['data'])
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment', filename=attachment['filename'])
            message.attach(part)

        response = self.client.send_raw_email(
            Source=self.sender,
            Destinations=destinations,
            RawMessage={'Data': message.as_string()}
        )
        return {'message_id': response['MessageId'], 'recipients': destinations}


class LINENotifier(LineNotifier):
    """LINE Messaging APIによるpush通知"""
    ENDPOINT = 'https://api.line.me/v2/bot/message/push'

    def __init__(self, channel_access_token: str, to: str):
        self.channel_access_token = channel_access_token
        self.to = to

    def send_line(self, text: str, image_urls: list[str]) -> dict:
        if len(text) > LINE_TEXT_MAX_LENGTH:
            text = f'{text[:LINE_TEXT_MAX_LENGTH - 1]}…'
        messages = [{'type': 'text', 'text': text}]
        for image_url in image_urls:
            messages.append({
                'type': 'image',
                'originalContentUrl': image_url,
                'previewImageUrl': image_url,
            })
        payload = json.dumps({
            'to': self.to,
            'messages': messages,
        }, ensure_ascii=False).encode('utf-8')
        request = urllib.request.Request(
            self.ENDPOINT,
            data=payload,
            headers={
                'Authorization': f'Bearer {self.channel_access_token}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                status_code = response.getcode()
                response.read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f'LINE Messaging API request failed (HTTP {e.code})') from None
        return {'status_code': status_code}


def get_notifier() -> Notifier:
    sender = os.environ.get('SES_SENDER', '')
    recipients_raw = os.environ.get('NOTIFY_RECIPIENTS', '')
    recipients = [r.strip() for r in recipients_raw.split(',') if r.strip()]
    return SESNotifier(sender=sender, recipients=recipients)


def get_line_notifier() -> LineNotifier:
    global _cached_line_token
    to = os.environ.get('LINE_NOTIFY_TO', '').strip()
    if not to:
        raise LineNotConfiguredError('LINE_NOTIFY_TOが設定されていません')
    if not _cached_line_token:
        parameter_name = os.environ.get(
            'LINE_TOKEN_PARAM', '/image-analysis/line-channel-access-token')
        ssm = boto3.client('ssm')
        try:
            response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
        except ssm.exceptions.ParameterNotFound:
            raise LineNotConfiguredError(
                f'LINEアクセストークンが設定されていません ({parameter_name})') from None
        _cached_line_token = response['Parameter']['Value']
    return LINENotifier(channel_access_token=_cached_line_token, to=to)
