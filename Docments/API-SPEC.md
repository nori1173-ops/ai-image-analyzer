# API仕様書

## テスト画面アクセス

| 項目 | 値 |
|------|-----|
| URL | https://image-analysis.example-cloud.com |
| アクセス条件 | 許可IP (203.0.113.1) からのみ |
| 認証 | Cognito ユーザーアカウント (メール/パスワード) |
| 対応ブラウザ | Chrome / Edge / Firefox (最新版) |

## Cognito認証の取得手順

### テスト画面から (自動)

1. https://image-analysis.example-cloud.com にアクセス
2. Amplify Authenticatorのログイン画面が表示
3. メールアドレス・パスワードを入力してサインイン
4. 以降のAPI呼び出しは自動的にJWTが付与される

### API直接呼び出し用 (手動トークン取得)

```bash
# Cognito トークン取得
aws cognito-idp initiate-auth \
  --client-id <USER_POOL_CLIENT_ID> \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=<email>,PASSWORD=<password> \
  --region ap-northeast-1

# レスポンスから IdToken を取得して使用
export COGNITO_TOKEN="eyJraWQi..."
```

## APIキー取得手順 (ワークフロー連携用)

1. AWSコンソール → API Gateway → APIキー → 対象キーの値を取得
2. または AWS CLI で取得:

```bash
aws apigateway get-api-keys --include-values \
  --region ap-northeast-1 \
  --query 'items[?name==`image-analysis-key`].value' \
  --output text
```

## 各エンドポイント呼び出しサンプル

### POST /api/analyze

#### curl (テスト画面用: Cognito JWT)

```bash
# 画像をbase64エンコード
IMAGE_B64=$(base64 -w 0 photo.jpg)

curl -X POST https://image-analysis.example-cloud.com/api/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $COGNITO_TOKEN" \
  -d "{
    \"image\": \"data:image/jpeg;base64,$IMAGE_B64\",
    \"target\": \"crack\",
    \"model\": \"gpt-4.1-mini\",
    \"detail\": \"low\"
  }"
```

#### curl (ワークフロー用: APIキー + Base64)

```bash
curl -X POST https://<api-gateway-domain>/prod/workflow/analyze \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d "{
    \"data\": \"$(base64 -w 0 photo.jpg)\",
    \"target\": \"crack\"
  }"
```

#### curl (ワークフロー用: APIキー + S3キー参照)

```bash
curl -X POST https://<api-gateway-domain>/prod/workflow/analyze \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "image_bucket": "<bucket-name>",
    "image_key": "path/to/image.jpg",
    "target": "crack"
  }'
```

#### Python

```python
import base64
import requests

with open("photo.jpg", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

response = requests.post(
    "https://image-analysis.example-cloud.com/api/analyze",
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cognito_token}"
    },
    json={
        "image": f"data:image/jpeg;base64,{image_b64}",
        "target": "crack",
        "detail": "low"
    }
)
print(response.json())
```

#### JavaScript (fetch)

```javascript
const file = document.querySelector('input[type="file"]').files[0]
const reader = new FileReader()
reader.onload = async () => {
  const response = await fetch('/api/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${idToken}`
    },
    body: JSON.stringify({
      image: reader.result,
      target: 'crack',
      detail: 'low'
    })
  })
  const result = await response.json()
  console.log(result)
}
reader.readAsDataURL(file)
```

### GET /api/health

```bash
curl https://image-analysis.example-cloud.com/api/health
# => {"status": "ok", "timestamp": "2026-03-04T12:00:00Z"}
```

## エラーレスポンスと対処法

エラーレスポンスは `{"error": "メッセージ"}` 形式で返却される。

| HTTP | error メッセージ | 原因 | 対処法 |
|------|-----------------|------|--------|
| 400 | image or data is required | image/data/image_url/image_bucket+image_keyが未指定 | いずれかを指定する |
| 400 | target is required | targetが未指定 | targetを指定する |
| 400 | Invalid JSON | リクエストボディが不正 | 正しいJSONを送信する |
| 400 | image_bucket and image_key are both required | S3参照の片方のみ指定 | 両方指定する |
| 400 | URL domain not allowed... | 許可外ドメインのURL | *.amazonaws.com のみ許可 |
| 400 | Image too large (max 20MB) | 20MB超過 | 画像を圧縮する |
| 401 | - | JWT無効/期限切れ | 再ログインしてトークン再取得 |
| 403 | Forbidden | オリジン検証失敗/APIキー無効 | 正しい経路でアクセス |
| 404 | Not Found | 不明なエンドポイント | パスとメソッドを確認 |

## ワークフロー連携 (external-system)

### ワークフローJSON定義サンプル

external-systemの `UploadByHttp` タスクを使用して本APIを呼び出す。

```json
{
  "name": "画像解析ワークフロー",
  "subscribe": {
    "topic": "NotificationTopic",
    "filter": {
      "subject": { "contains": "inspection" }
    }
  },
  "tasks": [
    {
      "type": "GetMessage",
      "name": "メッセージ取得"
    },
    {
      "type": "ChoiceAttachments",
      "name": "添付画像選択",
      "config": {
        "mimeTypes": ["image/jpeg", "image/png"]
      }
    },
    {
      "type": "UploadByHttp",
      "name": "画像解析API呼び出し",
      "config": {
        "url": "https://<api-gateway-domain>/prod/analyze",
        "method": "POST",
        "asJson": true,
        "headers": {
          "x-api-key": "<API_KEY>"
        },
        "bodyTemplate": {
          "target": "crack",
          "model": "gpt-4.1-mini",
          "detail": "low"
        }
      }
    }
  ]
}
```

### UploadByHttpの動作

1. `ChoiceAttachments` で選択された添付ファイル (`attachments[0]`) を取得
2. `base64.b64encode(attachment.payload)` でBase64化
3. `bodyTemplate` の内容に `data` (Base64) と `filename` を自動追加
4. 指定URLにPOST送信
