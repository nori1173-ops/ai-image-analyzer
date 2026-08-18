# API仕様書

OpenAPI定義のバージョンは **1.6.0**（`openapi/openapi.yaml`）である。

## テスト画面アクセス

| 項目 | 値 |
|------|-----|
| URL | https://image-analysis.example-cloud.com |
| アクセス条件 | 許可IP (203.0.113.10) からのみ |
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
  --query 'items[?contains(name, `api-key`)].{name: name, value: value}' \
  --output table
```

## AIプラットフォームとモデル指定

`model` を省略した場合は Amazon Bedrock Claude の `anthropic.claude-sonnet-5` を使用する。モデルIDの名前空間により、`anthropic.claude-*` は Amazon Bedrock Claude（Messages API）、`openai.gpt-*` は Amazon Bedrock GPT（Responses API）、プレフィックスなしの `claude-*` は Claude Platform on AWS（CPoA）へルーティングされる。Amazon Bedrock は IAM/SigV4 認証で利用し、APIキー・追加契約は不要である。対応する12モデル、リージョン、単価は [API詳細設計書](API-DESIGN.md) の「対応モデル」を参照する。

Bedrock Claude は Haiku 4.5 / Opus 4.7 / Opus 4.8 を東京、Sonnet 5 を米国東部で処理する。Bedrock GPT は米国東部（Ohio）で処理し、すべての呼び出しで `store:false` を送信する。

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
    \"target\": \"人物\",
    \"model\": \"anthropic.claude-sonnet-5\"
  }"
```

#### curl (ワークフロー用: APIキー)

```bash
curl -X POST https://<api-gateway-domain>/prod/workflow/analyze \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d "{
    \"data\": \"$(base64 -w 0 photo.jpg)\",
    \"filename\": \"photo.jpg\",
    \"target\": \"人物\"
  }"
```

#### curl (ワークフロー用: S3キー参照)

```bash
curl -X POST https://<api-gateway-domain>/prod/workflow/analyze \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "image_bucket": "mail-backend-repository-xxxxx",
    "image_key": "tmp/message-id/photo.jpg",
    "target": "人物"
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
        "target": "人物"
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
      target: '人物'
    })
  })
  const result = await response.json()
  console.log(result)
}
reader.readAsDataURL(file)
```

### POST /api/compare（画像比較・災害差分監視）

前回画像と今回画像の2枚を比較し、監視観点に基づいて災害危険度（none/low/medium/high）を判定する。定点カメラの定期観測（例: 10分／1時間間隔）での土砂災害・河川増水の予兆検知を想定。前回画像の保持・定期実行は呼び出し元の責務。

#### curl（テスト画面用: Cognito JWT）

```bash
BEFORE_B64=$(base64 -w 0 before.jpg)
AFTER_B64=$(base64 -w 0 after.jpg)

curl -X POST https://image-analysis.example-cloud.com/api/compare \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $COGNITO_TOKEN" \
  -d "{
    \"before_image\": \"data:image/jpeg;base64,$BEFORE_B64\",
    \"after_image\": \"data:image/jpeg;base64,$AFTER_B64\",
    \"perspective\": \"土砂崩れの予兆\",
    \"notify\": true,
    \"notify_to\": [\"devA@example.co.jp\"],
    \"notify_cc\": [\"team@example.co.jp\"],
    \"notify_line\": false
  }"
```

#### curl（ワークフロー用: APIキー + S3参照）

```bash
curl -X POST https://<api-gateway-domain>/prod/workflow/compare \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "before_image_bucket": "mail-backend-repository-xxxxx",
    "before_image_key": "tmp/prev/photo.jpg",
    "after_image_bucket": "mail-backend-repository-xxxxx",
    "after_image_key": "tmp/curr/photo.jpg",
    "perspective": "河川水位の上昇"
  }'
```

#### レスポンス例

```json
{
  "danger": true,
  "risk_level": "high",
  "reason": "斜面上部に新たな亀裂が確認できます。",
  "changes": "前回画像にはなかった土砂の堆積が発生しています。",
  "model": "anthropic.claude-sonnet-5",
  "elapsed_seconds": 3.45,
  "notified": true,
  "message_id": "0100018f-xxxx-xxxx"
}
```

#### notify（メール・LINE通知）の挙動

- `notify=true` かつ `danger=true`（危険検知）のときのみ、判定理由と写真2枚（前回・今回）を添付したメールを送信する。
- 宛先は `notify_to` / `notify_cc` / `notify_bcc`（各 string 配列・最大10件・メール形式検証）で指定でき、`notify_to` を省略した場合はサーバー既定（`NOTIFY_RECIPIENTS`、既定 devA@example.co.jp）に送信する。BCC はメールヘッダに載せず SES の Destinations にのみ含める。宛先ドメインの制限はない（認証済み経路のみで利用されるため許容）。不正な宛先（配列でない・メール形式でない・10件超）は 400。
- `notify_line=true` かつ危険検知時は LINE Messaging API でも通知する（テキスト＋画像2枚）。画像は専用S3バケットに一時保存し presigned URL（6時間失効）で送信する。サーバー側でLINE設定（チャネルアクセストークン・宛先ID）が未構成の場合はスキップされ、`line_skip_reason` を返す。
- 通知送信（メール／LINE）に失敗しても判定結果は 200 で返り、レスポンスの `notify_error`／`line_error` に理由が入る。
- モデルは `anthropic.claude-*`（Bedrock Claude）、`openai.gpt-*`（Bedrock GPT）、またはプレフィックスなしの `claude-*`（CPoA）から選択する。省略時は `anthropic.claude-sonnet-5`。`detail`（解像度）は廃止済み（送信されても無視）、`effort`（`low`〜`max`）は対応モデル（Sonnet 等）のみ有効。

### GET /api/health

```bash
curl https://image-analysis.example-cloud.com/api/health
# => {"status": "ok", "timestamp": "2026-03-04T12:00:00Z"}
```

## エラーコード一覧と対処法

| HTTP | コード | 原因 | 対処法 |
|------|--------|------|--------|
| 400 | MISSING_IMAGE | image/dataが未指定 | いずれかを指定する |
| 400 | MISSING_TARGET | targetが未指定 | targetを指定する |
| 400 | INVALID_IMAGE | base64デコード失敗 | 画像を再エンコード |
| 400 | IMAGE_TOO_LARGE | 20MB超過 | 画像を圧縮する |
| 401 | UNAUTHORIZED | JWT無効/期限切れ | 再ログインしてトークン再取得 |
| 403 | FORBIDDEN | APIキー無効またはIP制限 | キーとIPを確認 |
| 500 | AI_ERROR | AI推論サービス障害（Amazon Bedrock / Claude Platform on AWS） | 時間を置いてリトライ |
| 504 | TIMEOUT | 処理タイムアウト | 画像を縮小して再試行 |

## ワークフロー連携 (mail-backend)

### ワークフローJSON定義サンプル

mail-backendの `HttpUpload` タスクを使用して本APIを呼び出す。

```json
{
  "name": "画像解析ワークフロー",
  "subscribe": {
    "topic": "DeliverTopic",
    "filter": {
      "subject": { "contains": "観測カメラ" }
    }
  },
  "tasks": [
    {
      "type": "FetchMessage",
      "name": "メッセージ取得"
    },
    {
      "type": "SelectAttachments",
      "name": "添付画像選択",
      "config": {
        "mimeTypes": ["image/jpeg", "image/png"]
      }
    },
    {
      "type": "HttpUpload",
      "name": "画像解析API呼び出し",
      "config": {
        "url": "https://<api-gateway-domain>/prod/analyze",
        "method": "POST",
        "asJson": true,
        "headers": {
          "x-api-key": "<API_KEY>"
        },
        "bodyTemplate": {
          "target": "人物",
          "model": "anthropic.claude-sonnet-5"
        }
      }
    }
  ]
}
```

### HttpUploadの動作

1. `SelectAttachments` で選択された添付ファイル (`attachments[0]`) を取得
2. `base64.b64encode(attachment.payload)` でBase64化
3. `bodyTemplate` の内容に `data` (Base64) と `filename` を自動追加
4. 指定URLにPOST送信
