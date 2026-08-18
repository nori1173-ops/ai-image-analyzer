# API詳細設計書

## エンドポイント一覧

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| POST | /api/analyze | Cognito JWT | 画像解析（テスト画面用） |
| POST | /api/workflow/analyze | APIキー | 画像解析（ワークフロー用） |
| POST | /api/compare | Cognito JWT | 画像比較・災害差分監視（テスト画面用） |
| POST | /api/workflow/compare | APIキー | 画像比較・災害差分監視（ワークフロー用） |
| GET | /api/health | なし（オリジン検証あり） | ヘルスチェック |

※ CloudFront経由時 `/api/*` → API Gateway `/prod/*` にリライトされる
※ `/analyze`・`/compare`・`/health` は Origin Verify Header を検証し、CloudFront を経由しない直接アクセスは 403 を返す

## 認証方式

![API-DESIGN-diagram-1](images/API-DESIGN-diagram-1.svg)

| 方式 | ヘッダー | 用途 |
|------|---------|------|
| Cognito JWT | `Authorization: Bearer <token>` | テスト画面（/api/analyze） |
| APIキー | `x-api-key: <key>` | ワークフロー連携（/api/workflow/analyze） |
| なし | - | /api/health のみ |

## POST /api/analyze

テスト画面用の画像解析エンドポイント。Cognito JWTによる認証が必要。

### リクエスト

```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQ...",
  "target": "人物",
  "model": "anthropic.claude-sonnet-5"
}
```

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|------|------|----------|------|
| image | string | ※ | - | base64画像 (data URI or raw) |
| data | string | ※ | - | raw base64 (ワークフロー用、imageと排他) |
| image_bucket | string | - | - | S3バケット名（image_keyと組み合わせ） |
| image_key | string | - | - | S3オブジェクトキー（image_bucketと組み合わせ） |
| image_url | string | - | - | 画像URL（*.amazonaws.comのみ） |
| filename | string | - | - | ファイル名 |
| target | string | Yes | - | 検出対象オブジェクト |
| model | string | - | DEFAULT_MODEL（現状 `anthropic.claude-sonnet-5`） | 後述の対応モデルを参照。`anthropic.claude-*` / `openai.gpt-*` は Amazon Bedrock、プレフィックスなしの `claude-*` は Claude Platform on AWS（CPoA）で処理する |
| effort | string | - | モデル既定 | low / medium / high / xhigh / max（対応モデルのみ有効、不正値は400） |

※ `image_bucket`+`image_key` / `image_url` / `image` / `data` のいずれか必須（優先順位順）
※ `detail`（解像度）は廃止済み。後方互換でリクエストに含まれても無視される。

### 対応モデル

`get_analyzer()` はモデルIDの名前空間で3経路にルーティングする。省略時はサーバー側の `DEFAULT_MODEL`（現状 `anthropic.claude-sonnet-5`）を使用する。フロントエンドで選択できる対応モデルは次の12件である。

| モデルID | プラットフォーム | 処理リージョン | 入力/出力単価（$/1Mトークン） | 備考 |
|----------|------------------|----------------|-------------------------------|------|
| `anthropic.claude-sonnet-5` | Amazon Bedrock Claude | 米国（us-east-1） | $2 / $10（2026-09-01以降 $3 / $15） | **既定・推奨**。東京未提供のため米国処理 |
| `anthropic.claude-haiku-4-5` | Amazon Bedrock Claude | 東京（ap-northeast-1） | $1 / $5 | 低コスト |
| `anthropic.claude-opus-4-7` | Amazon Bedrock Claude | 東京（ap-northeast-1） | $5 / $25 | |
| `anthropic.claude-opus-4-8` | Amazon Bedrock Claude | 東京（ap-northeast-1） | $5 / $25 | |
| `openai.gpt-5.6-terra` | Amazon Bedrock GPT | 米国（us-east-2） | $2.5 / $15 | |
| `openai.gpt-5.6-luna` | Amazon Bedrock GPT | 米国（us-east-2） | $1 / $6 | 低コスト |
| `openai.gpt-5.6-sol` | Amazon Bedrock GPT | 米国（us-east-2） | $5 / $30 | |
| `openai.gpt-5.5` | Amazon Bedrock GPT | 米国（us-east-2） | $5.5 / $33 | |
| `openai.gpt-5.4` | Amazon Bedrock GPT | 米国（us-east-2） | $2.75 / $16.5 | |
| `claude-sonnet-5` | Claude Platform on AWS | 米国 | $2 / $10（2026-09-01以降 $3 / $15） | |
| `claude-haiku-4-5` | Claude Platform on AWS | 米国 | $1 / $5 | |
| `claude-sonnet-4-6` | Claude Platform on AWS | 米国 | $3 / $15 | |

- `anthropic.claude-*` は Amazon Bedrock Claude の Messages API（`https://bedrock-mantle.{region}.api.aws/anthropic/v1/messages`）を `AnthropicBedrockMantle` で呼び出す。`tool_use` を強制して構造化出力を得る。
- `openai.gpt-*` は Amazon Bedrock GPT の Responses API（`https://bedrock-mantle.{region}.api.aws/openai/v1/responses`）を `bedrock-mantle` サービス名の SigV4 で呼び出す。全リクエストで `store:false` を送信し、会話の30日保存を無効化する。
- プレフィックスなしの `claude-*` は従来どおり Claude Platform on AWS（Anthropic 運営）を `AnthropicAWS` で呼び出す。利用には環境変数 `ANTHROPIC_AWS_WORKSPACE_ID` と、Lambda ロールへの `aws-external-anthropic:CreateInference`・`sts:GetWebIdentityToken`・`sts:TagGetWebIdentityToken` 権限が必要である。
- Amazon Bedrock の各経路は Lambda ロールの `bedrock-mantle:CreateInference`（Resource `*`）を用いる。モデルアクセスページは廃止されており、初回呼び出しでモデルが自動有効化されるため、APIキー・追加契約は不要である。
- `effort`（推論エフォート、`low`/`medium`/`high`/`xhigh`/`max`）は対応するモデル（`claude-sonnet-5` 等）でのみ有効。非対応モデル（`claude-haiku-4-5` 等）に指定するとAIプロバイダ側でエラーになる場合がある。不正値は 400。

### レスポンス (200 OK)

```json
{
  "found": true,
  "context": "この画像に「人物」は存在しますか？",
  "answer": "はい、画像の右側に人物が1名確認できます。",
  "confidence": 92,
  "model": "anthropic.claude-sonnet-5",
  "elapsed_seconds": 2.34,
  "usage": {
    "prompt_tokens": 1200,
    "completion_tokens": 85,
    "total_tokens": 1285
  }
}
```

| フィールド | 型 | 説明 |
|-----------|------|------|
| found | boolean | 検出有無 |
| context | string | AIに送信したプロンプト |
| answer | string | AIの返答 |
| confidence | number | 確信度 (0-100) |
| model | string | 使用モデル名 |
| elapsed_seconds | number | 処理時間（秒） |
| usage | object | トークン使用量 |

## POST /api/workflow/analyze

ワークフロー連携用の画像解析エンドポイント。リクエスト/レスポンス仕様は POST /api/analyze と同一。
認証方式のみ異なり、APIキー（`x-api-key` ヘッダー）を使用する。

## POST /api/compare

前回画像・今回画像の2枚を比較し、監視観点（`perspective`）に基づいて災害危険度を判定する災害差分監視エンドポイント。定点カメラの定期観測（例: 10分／1時間間隔）での土砂災害・河川増水の予兆検知を想定する。落ち葉・影・天候・明るさ・小動物など災害と無関係な差分は無視する。Cognito JWT による認証が必要（ワークフロー用は POST /api/workflow/compare、APIキー認証）。

> 前回画像の保持・定期実行は呼び出し元（ワークフロー等）の責務。本APIは受け取った2枚を都度比較するステートレスなAPIとして動作する。

### リクエスト

```json
{
  "before_image": "data:image/jpeg;base64,/9j/4AAQ...",
  "after_image": "data:image/jpeg;base64,/9j/4AAQ...",
  "perspective": "土砂崩れの予兆",
  "model": "anthropic.claude-sonnet-5",
  "notify": false
}
```

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|------|------|----------|------|
| before_image / before_data / before_image_url / before_image_bucket+before_image_key | string | ※ | - | 前回画像（4方式のいずれか。優先順位順） |
| after_image / after_data / after_image_url / after_image_bucket+after_image_key | string | ※ | - | 今回画像（4方式のいずれか。優先順位順） |
| perspective | string | Yes | - | 監視観点（災害予兆を判定する基準） |
| model | string | - | DEFAULT_MODEL（現状 `anthropic.claude-sonnet-5`） | 「対応モデル」参照。モデルIDの名前空間によりAmazon BedrockまたはCPoAへルーティング |
| effort | string | - | モデル既定 | low / medium / high / xhigh / max（対応モデルのみ有効、不正値は400） |
| notify | boolean | - | false | 危険判定時に写真添付メールを送信するか |
| notify_to | string[] | - | サーバー既定 | 通知メールのTo宛先（最大10件・メール形式検証・省略時は `NOTIFY_RECIPIENTS`） |
| notify_cc | string[] | - | - | 通知メールのCC宛先（最大10件、任意） |
| notify_bcc | string[] | - | - | 通知メールのBCC宛先（最大10件、任意。ヘッダには載せずSES Destinationsのみに指定） |
| notify_line | boolean | - | false | 危険判定時にLINE Messaging APIで通知（テキスト＋画像2枚）するか |

※ 前回・今回それぞれ、画像の指定方法は `image`/`data`/`image_url`/`image_bucket`+`image_key` と同じ4方式に `before_`/`after_` プレフィックスを付けたもの。
※ `notify_to`/`notify_cc`/`notify_bcc` は string 配列で各最大10件。要素がメール形式でない・配列でない・10件超のいずれかで 400 `Invalid notify_to`（該当フィールド名）を返す。

### レスポンス (200 OK)

```json
{
  "danger": true,
  "risk_level": "high",
  "reason": "斜面上部に新たな亀裂と土砂の崩落が確認できます。",
  "changes": "前回画像にはなかった土砂の堆積が斜面下部に発生しています。",
  "model": "anthropic.claude-sonnet-5",
  "usage": { "prompt_tokens": 2100, "completion_tokens": 120, "total_tokens": 2220 },
  "elapsed_seconds": 3.45,
  "notified": true,
  "message_id": "0100018f-xxxx-xxxx",
  "line_notified": false
}
```

| フィールド | 型 | 説明 |
|-----------|------|------|
| danger | boolean | 災害危険を検知したか |
| risk_level | string | 危険度（none / low / medium / high） |
| reason | string | 判定理由（日本語） |
| changes | string | 検出された変化の説明 |
| model | string | 使用モデル名 |
| usage | object | トークン使用量 |
| elapsed_seconds | number | 処理時間（秒） |
| notified | boolean | 通知メールを送信したか |
| message_id | string | 送信メールのMessageID（通知成功時のみ） |
| notify_error | string | メール送信に失敗した場合のエラー内容（通知失敗時のみ。API自体は200を維持） |
| line_notified | boolean | LINE通知を送信したか |
| line_skip_reason | string | LINE設定が未構成でスキップした場合の理由（該当時のみ） |
| line_error | string | LINE送信に失敗した場合のエラー内容（該当時のみ。API自体は200を維持） |

- メール通知は `notify=true` かつ `danger=true` の場合のみ送信。宛先は `notify_to`/`notify_cc`/`notify_bcc` で指定でき、`notify_to` 省略時はサーバー既定（`NOTIFY_RECIPIENTS`）に送信する。BCC はメールヘッダに載せず SES Destinations にのみ含める。宛先ドメインの制限はない（認証済み経路のみで利用されるため許容。詳細はセキュリティ設計書）。
- LINE通知は `notify_line=true` かつ `danger=true` の場合のみ。テキストと画像2枚（前回・今回）を LINE Messaging API で push する。画像は専用S3バケットに一時保存し presigned URL（6時間失効）で送信する。サーバー側でLINE設定（チャネルアクセストークン `/image-analysis/line-channel-access-token`・宛先 `LINE_NOTIFY_TO`）が未構成の場合はスキップし `line_skip_reason` を返す。
- 通知（メール／LINE）に失敗しても判定結果は 200 で返し、メールは `notify_error`、LINEは `line_error` に理由を格納する。

## POST /api/workflow/compare

ワークフロー連携用の画像比較エンドポイント。リクエスト/レスポンス仕様は POST /api/compare と同一。認証方式のみ異なり、APIキー（`x-api-key` ヘッダー）を使用する。

## GET /api/health

### レスポンス (200 OK)

```json
{
  "status": "ok",
  "timestamp": "2026-03-04T12:00:00Z"
}
```

## エラーコード一覧

| HTTP | エラーメッセージ | 説明 | 対処法 |
|------|----------------|------|--------|
| 400 | image or data is required | image/dataが未指定 | image, data, image_url, image_bucket+image_key のいずれかを指定 |
| 400 | target is required | target（/analyze）が未指定 | target を指定 |
| 400 | perspective is required | perspective（/compare）が未指定 | perspective を指定 |
| 400 | before image is required / after image is required | 比較の前回/今回画像が未指定 | before_/after_ の画像を指定 |
| 400 | Invalid model | `claude` / `anthropic.claude` / `openai.gpt` 以外の名前空間を指定 | 対応モデルのモデルIDを指定 |
| 400 | Invalid effort (low\|medium\|high\|xhigh\|max) | effort が許可値以外 | 有効な effort を指定 |
| 400 | Invalid notify_to / notify_cc / notify_bcc | 通知宛先が配列でない・メール形式でない・10件超 | メール形式で各最大10件を指定 |
| 400 | Invalid JSON | JSON解析失敗 | 正しいJSONを送信 |
| 400 | image_bucket and image_key are both required | S3パラメータ不完全 | 両方を指定 |
| 400 | 指定されたバケットは許可されていません | 許可リスト外バケット | ALLOWED_IMAGE_BUCKETS に登録されたバケットのみ |
| 400 | URL domain not allowed / リダイレクトは許可されていません | URLドメイン不正・リダイレクト検出 | https の *.amazonaws.com のみ許可（リダイレクト不可） |
| 400 | Image too large (max 20MB) | 画像サイズ超過 | 画像を圧縮 |
| 401 | Unauthorized | JWT無効/期限切れ | トークンを再取得 |
| 403 | Forbidden | オリジン検証失敗/APIキー無効 | 正しい経路・キーを使用 |
| 404 | Not Found | 未定義のパス・メソッド | エンドポイントを確認 |
| 500 | AI_ERROR | AI API呼び出し失敗 | リトライ |

※ 画像比較で `notify=true`（メール）／`notify_line=true`（LINE）の通知送信に失敗した場合でもAPIは 200 を返し、レスポンスの `notify_error`／`line_error` に理由を格納する（判定結果は返却される）。

### エラーレスポンス形式

```json
{
  "error": "target is required"
}
```

## curlサンプル

### テスト画面用 (Cognito JWT)

```bash
curl -X POST https://image-analysis.example-cloud.com/api/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $COGNITO_TOKEN" \
  -d '{
    "image": "data:image/jpeg;base64,/9j/4AAQ...",
    "target": "人物"
  }'
```

### ワークフロー用 (APIキー)

```bash
curl -X POST https://{api-gateway-domain}/prod/workflow/analyze \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "data": "/9j/4AAQ...",
    "filename": "photo.jpg",
    "target": "人物"
  }'
```

### 画像比較 (Cognito JWT)

```bash
curl -X POST https://image-analysis.example-cloud.com/api/compare \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $COGNITO_TOKEN" \
  -d '{
    "before_image": "data:image/jpeg;base64,/9j/4AAQ...",
    "after_image": "data:image/jpeg;base64,/9j/4AAQ...",
    "perspective": "土砂崩れの予兆",
    "notify": true
  }'
```

### 画像比較 (APIキー・S3参照)

```bash
curl -X POST https://{api-gateway-domain}/prod/workflow/compare \
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

### ヘルスチェック

```bash
curl https://image-analysis.example-cloud.com/api/health
```

## 認証フロー シーケンス図

![API-DESIGN-diagram-2](images/API-DESIGN-diagram-2.svg)
