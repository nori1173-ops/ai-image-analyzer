import json
from openai import OpenAI


class ImageAnalyzer:
    """AIプロバイダー抽象レイヤー"""
    def analyze(self, base64_image: str, target: str, model: str = "gpt-4.1-mini", detail: str = "low") -> dict:
        raise NotImplementedError


class OpenAIAnalyzer(ImageAnalyzer):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def analyze(self, base64_image: str, target: str, model: str = "gpt-4.1-mini", detail: str = "low") -> dict:
        system_prompt = (
            "あなたは画像解析の専門家です。\n"
            "ユーザーが指定したオブジェクトが画像内に存在するかを判定してください。\n"
            "必ず以下のJSON形式で回答してください:\n"
            "{\n"
            '  "found": true/false,\n'
            '  "answer": "詳細な説明",\n'
            '  "confidence": 0〜100の整数\n'
            "}"
        )

        user_prompt = f"この画像に「{target}」は存在しますか？"

        response = self.client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": detail
                    }}
                ]}
            ],
            max_tokens=500
        )

        result = json.loads(response.choices[0].message.content)
        result["context"] = user_prompt
        result["model"] = response.model
        result["usage"] = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        return result


def get_analyzer(api_key: str) -> ImageAnalyzer:
    return OpenAIAnalyzer(api_key=api_key)
