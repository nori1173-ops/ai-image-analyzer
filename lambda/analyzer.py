import json
import os
from urllib.request import Request, urlopen

from anthropic import AnthropicAWS, AnthropicBedrockMantle
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import get_session


ANALYSIS_SYSTEM_PROMPT = (
    "あなたは画像解析の専門家です。\n"
    "ユーザーが指定したオブジェクトが画像内に存在するかを判定し、"
    "report_analysis ツールで結果を報告してください。"
)

COMPARISON_SYSTEM_PROMPT = (
    "あなたは定点カメラの前回画像と今回画像を比較し、"
    "土砂災害や河川増水などの災害予兆を検知する専門家です。\n"
    "指定された監視観点に基づいて災害危険度を判定し、"
    "report_comparison ツールで結果を報告してください。\n"
    "落ち葉・影・天候・明るさ・小動物など、災害と無関係な変化は無視し danger=false としてください。\n"
    "reason は日本語で具体的に記述してください。"
)

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "found": {"type": "boolean"},
        "answer": {"type": "string"},
        "confidence": {"type": "integer", "minimum": 0, "maximum": 100}
    },
    "required": ["found", "answer", "confidence"]
}

COMPARISON_SCHEMA = {
    "type": "object",
    "properties": {
        "danger": {"type": "boolean"},
        "risk_level": {
            "type": "string",
            "enum": ["none", "low", "medium", "high"]
        },
        "reason": {"type": "string"},
        "changes": {"type": "string"}
    },
    "required": ["danger", "risk_level", "reason", "changes"]
}

BEDROCK_CLAUDE_MODEL_REGIONS = {
    "anthropic.claude-haiku-4-5": (
        "BEDROCK_JP_REGION", "ap-northeast-1"),
    "anthropic.claude-opus-4-7": (
        "BEDROCK_JP_REGION", "ap-northeast-1"),
    "anthropic.claude-opus-4-8": (
        "BEDROCK_JP_REGION", "ap-northeast-1"),
    "anthropic.claude-sonnet-5": (
        "BEDROCK_US_REGION", "us-east-1")
}


def _analysis_user_prompt(target: str) -> str:
    return f"この画像に「{target}」は存在しますか？"


def _comparison_user_prompt(perspective: str) -> str:
    return f"監視観点「{perspective}」で災害危険度を判定してください"


class ImageAnalyzer:
    """AIプロバイダー抽象レイヤー"""
    def analyze(self, base64_image: str, target: str, model: str = "claude-haiku-4-5", detail: str = "low", effort: str = None) -> dict:
        raise NotImplementedError

    def compare(self, base64_before: str, base64_after: str, perspective: str, model: str = "claude-haiku-4-5", detail: str = "low", effort: str = None) -> dict:
        raise NotImplementedError


def _detect_media_type(base64_image: str) -> str:
    if base64_image.startswith('iVBOR'):
        return 'image/png'
    return 'image/jpeg'


class ClaudeAnalyzer(ImageAnalyzer):
    """Claude Platform on AWS (SigV4認証、tool_use強制で構造化出力)"""
    def __init__(self):
        self.client = AnthropicAWS()

    def _get_client(self, model: str):
        return self.client

    def analyze(self, base64_image: str, target: str, model: str = "claude-sonnet-5", detail: str = "low", effort: str = None) -> dict:
        system_prompt = ANALYSIS_SYSTEM_PROMPT
        user_prompt = _analysis_user_prompt(target)

        tools = [{
            "name": "report_analysis",
            "description": "画像解析結果を報告する",
            "input_schema": ANALYSIS_SCHEMA
        }]

        request_kwargs = {
            "model": model,
            "max_tokens": 500,
            "system": system_prompt,
            "tools": tools,
            "tool_choice": {"type": "tool", "name": "report_analysis"},
            "messages": [
                {"role": "user", "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": _detect_media_type(base64_image),
                        "data": base64_image
                    }},
                    {"type": "text", "text": user_prompt}
                ]}
            ]
        }
        if effort:
            request_kwargs["output_config"] = {"effort": effort}
        response = self._get_client(model).messages.create(**request_kwargs)

        tool_input = None
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                tool_input = block.input
                break
        if tool_input is None:
            raise ValueError("tool_use ブロックが見つかりませんでした")

        result = dict(tool_input)
        result["context"] = user_prompt
        result["model"] = model
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        result["usage"] = {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
        return result

    def compare(self, base64_before: str, base64_after: str, perspective: str, model: str = "claude-sonnet-5", detail: str = "low", effort: str = None) -> dict:
        system_prompt = COMPARISON_SYSTEM_PROMPT

        tools = [{
            "name": "report_comparison",
            "description": "2枚の画像比較による災害危険度判定結果を報告する",
            "input_schema": COMPARISON_SCHEMA
        }]

        request_kwargs = {
            "model": model,
            "max_tokens": 1000,
            "system": system_prompt,
            "tools": tools,
            "tool_choice": {"type": "tool", "name": "report_comparison"},
            "messages": [
                {"role": "user", "content": [
                    {"type": "text", "text": "前回の画像:"},
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": _detect_media_type(base64_before),
                        "data": base64_before
                    }},
                    {"type": "text", "text": "今回の画像:"},
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": _detect_media_type(base64_after),
                        "data": base64_after
                    }},
                    {"type": "text", "text": _comparison_user_prompt(perspective)}
                ]}
            ]
        }
        if effort:
            request_kwargs["output_config"] = {"effort": effort}
        response = self._get_client(model).messages.create(**request_kwargs)

        tool_input = None
        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                tool_input = block.input
                break
        if tool_input is None:
            raise ValueError("tool_use ブロックが見つかりませんでした")

        result = dict(tool_input)
        result["model"] = model
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        result["usage"] = {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
        return result


class BedrockClaudeAnalyzer(ClaudeAnalyzer):
    """Amazon Bedrock Claude (Mantle / SigV4認証)"""
    def __init__(self):
        self._clients = {}

    def _get_client(self, model: str):
        region_env, default_region = BEDROCK_CLAUDE_MODEL_REGIONS.get(
            model, ("BEDROCK_JP_REGION", "ap-northeast-1"))
        region = os.environ.get(region_env, default_region)
        if region not in self._clients:
            self._clients[region] = AnthropicBedrockMantle(aws_region=region)
        return self._clients[region]


class BedrockGPTAnalyzer(ImageAnalyzer):
    """Amazon Bedrock GPT (Mantle Responses API / SigV4認証)"""
    def __init__(self):
        self.region = os.environ.get("BEDROCK_GPT_REGION", "us-east-2")

    @staticmethod
    def _image_block(base64_image: str) -> dict:
        media_type = _detect_media_type(base64_image)
        return {
            "type": "input_image",
            "image_url": f"data:{media_type};base64,{base64_image}"
        }

    @staticmethod
    def _text_format(name: str, schema: dict) -> dict:
        return {
            "format": {
                "type": "json_schema",
                "name": name,
                "strict": True,
                "schema": {**schema, "additionalProperties": False}
            }
        }

    def _send_response(self, payload: dict) -> dict:
        url = (
            f"https://bedrock-mantle.{self.region}.api.aws"
            "/openai/v1/responses"
        )
        request_body = json.dumps(
            payload, ensure_ascii=False).encode("utf-8")
        aws_request = AWSRequest(
            method="POST",
            url=url,
            data=request_body,
            headers={"Content-Type": "application/json"}
        )
        credentials = get_session().get_credentials()
        if credentials is None:
            raise ValueError("AWS認証情報が見つかりませんでした")
        SigV4Auth(
            credentials.get_frozen_credentials(),
            "bedrock-mantle",
            self.region
        ).add_auth(aws_request)
        request = Request(
            url,
            data=request_body,
            headers=dict(aws_request.headers.items()),
            method="POST"
        )
        with urlopen(request, timeout=240) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _parse_result(response: dict) -> dict:
        output_text = None
        for output in response.get("output", []):
            if output.get("type") != "message":
                continue
            for content in output.get("content", []):
                if content.get("type") == "output_text":
                    output_text = content.get("text")
                    break
            if output_text is not None:
                break
        if output_text is None:
            raise ValueError("output_text が見つかりませんでした")
        try:
            result = json.loads(output_text)
        except (json.JSONDecodeError, TypeError) as error:
            raise ValueError("output_text のJSON解析に失敗しました") from error
        if not isinstance(result, dict):
            raise ValueError("output_text がJSONオブジェクトではありません")
        return result

    @staticmethod
    def _add_metadata(result: dict, response: dict, model: str) -> dict:
        input_tokens = response["usage"]["input_tokens"]
        output_tokens = response["usage"]["output_tokens"]
        result["model"] = model
        result["usage"] = {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
        return result

    def analyze(self, base64_image: str, target: str, model: str = "openai.gpt-5.5", detail: str = "low", effort: str = None) -> dict:
        user_prompt = _analysis_user_prompt(target)
        payload = {
            "model": model,
            "store": False,
            "max_output_tokens": 4000,
            "input": [
                {
                    "role": "system",
                    "content": [{
                        "type": "input_text",
                        "text": ANALYSIS_SYSTEM_PROMPT
                    }]
                },
                {
                    "role": "user",
                    "content": [
                        self._image_block(base64_image),
                        {"type": "input_text", "text": user_prompt}
                    ]
                }
            ],
            "text": self._text_format("report_analysis", ANALYSIS_SCHEMA)
        }
        if effort:
            payload["reasoning"] = {"effort": effort}
        response = self._send_response(payload)
        result = self._parse_result(response)
        result["context"] = user_prompt
        return self._add_metadata(result, response, model)

    def compare(self, base64_before: str, base64_after: str, perspective: str, model: str = "openai.gpt-5.5", detail: str = "low", effort: str = None) -> dict:
        payload = {
            "model": model,
            "store": False,
            "max_output_tokens": 4000,
            "input": [
                {
                    "role": "system",
                    "content": [{
                        "type": "input_text",
                        "text": COMPARISON_SYSTEM_PROMPT
                    }]
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "前回の画像:"},
                        self._image_block(base64_before),
                        {"type": "input_text", "text": "今回の画像:"},
                        self._image_block(base64_after),
                        {
                            "type": "input_text",
                            "text": _comparison_user_prompt(perspective)
                        }
                    ]
                }
            ],
            "text": self._text_format(
                "report_comparison", COMPARISON_SCHEMA)
        }
        if effort:
            payload["reasoning"] = {"effort": effort}
        response = self._send_response(payload)
        result = self._parse_result(response)
        return self._add_metadata(result, response, model)


def get_analyzer(model: str) -> ImageAnalyzer:
    if model.startswith("anthropic.claude"):
        return BedrockClaudeAnalyzer()
    if model.startswith("openai.gpt"):
        return BedrockGPTAnalyzer()
    if model.startswith("claude"):
        return ClaudeAnalyzer()
    raise ValueError(f"未対応のモデルです: {model}")
