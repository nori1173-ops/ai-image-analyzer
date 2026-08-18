# 画像解析API (Image Analysis)

観測カメラ等の画像をAIで判定するAPI。2つのモードを提供する。

- **単一画像解析**: 1枚の画像に指定オブジェクト（人物、車両等）が存在するか判定
- **画像比較（災害差分監視）**: 前回・今回の2枚を比較し、監視観点に基づき災害危険度を判定。危険検知時はメール通知（任意）

AI基盤は Amazon Bedrock Claude、Amazon Bedrock GPT、Claude Platform on AWS（CPoA）の3プラットフォーム構成。既定モデルは Bedrock Claude の `anthropic.claude-sonnet-5` で、Lambda 実行ロールの IAM/SigV4 認証により呼び出す（AIサービス用APIキー・Bedrockの追加契約不要）。モデルIDの `anthropic.claude-*` / `openai.gpt-*` はBedrock、プレフィックスなしの `claude-*` はCPoAへルーティングする。

Bedrock Claude は Haiku 4.5 / Opus 4.7 / Opus 4.8 を東京、Sonnet 5 を米国東部で処理する。Bedrock GPT は米国東部（Ohio）で処理し、会話保存を無効化する `store:false` を固定送信する。対応モデルと単価は [API詳細設計書](Docments/API-DESIGN.md)、監視コストは [料金見積](Docments/COST-ESTIMATE.md) を参照。

## テスト画面

| 項目 | 値 |
|------|-----|
| URL | https://image-analysis.example-cloud.com |
| アクセス条件 | 許可IPからのみ |
| 認証 | Cognito (メール/パスワード) |
| ユーザーID | demouser |
| パスワード | ******** |

## 利用手順

1. https://image-analysis.example-cloud.com にアクセス
2. メールアドレス・パスワードでログイン
3. タブで「単一画像解析」または「画像比較（災害差分監視）」を選択
4. 画像をドラッグ&ドロップまたはクリックでアップロード（比較モードは前回・今回の2枚）
5. 単一解析は「見つけたいもの」、比較は「監視観点」を入力
6. 必要に応じてモデルを選択（Amazon Bedrock / CPoAでグループ表示。?ボタンでプラットフォームの説明を確認。CostPanelで賢さ（目安）・単価・監視コストを確認。比較は危険検知時のメール通知〈To/CC/BCC 指定可〉・LINE通知を選択可能）
7. 「解析する」／「比較実行」ボタンをクリックし、結果を確認

## API直接呼び出し

### curl (Cognito JWT認証)

```bash
IMAGE_B64=$(base64 -w 0 photo.jpg)
curl -X POST https://image-analysis.example-cloud.com/api/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $COGNITO_TOKEN" \
  -d "{\"image\": \"data:image/jpeg;base64,$IMAGE_B64\", \"target\": \"人物\"}"
```

### curl (APIキー認証 - ワークフロー用)

```bash
curl -X POST https://<api-gateway-domain>/prod/analyze \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d "{\"data\": \"$(base64 -w 0 photo.jpg)\", \"target\": \"人物\"}"
```

### curl (画像比較・災害差分監視)

```bash
curl -X POST https://image-analysis.example-cloud.com/api/compare \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $COGNITO_TOKEN" \
  -d "{
    \"before_image\": \"data:image/jpeg;base64,$(base64 -w 0 before.jpg)\",
    \"after_image\": \"data:image/jpeg;base64,$(base64 -w 0 after.jpg)\",
    \"perspective\": \"土砂崩れの予兆\",
    \"notify\": true
  }"
```

`notify=true` かつ危険検知時のみ、写真2枚を添付したメールを送信する（宛先は `notify_to`/`notify_cc`/`notify_bcc` で指定可、省略時はサーバー既定）。`notify_line=true` で LINE 通知（テキスト＋画像2枚）も送信できる。

### ヘルスチェック

```bash
curl https://image-analysis.example-cloud.com/api/health
```

## エンドポイント一覧

| メソッド | パス | 認証 | 説明 |
|---------|------|------|------|
| POST | /api/analyze | Cognito JWT | 単一画像解析（テスト画面用） |
| POST | /api/workflow/analyze | APIキー | 単一画像解析（ワークフロー用） |
| POST | /api/compare | Cognito JWT | 画像比較・災害差分監視（テスト画面用） |
| POST | /api/workflow/compare | APIキー | 画像比較・災害差分監視（ワークフロー用） |
| GET | /api/health | なし（オリジン検証あり） | ヘルスチェック |

## ワークフロー連携

mail-backendの `HttpUpload` タスクから呼び出し可能。プログラム修正不要。

1. DeliverTopic SNSでメール受信を検知
2. FetchMessage → SelectAttachments → HttpUpload の順で処理
3. 画像は自動的にBase64化されPOSTされる
4. 詳細は `Docments/API-SPEC.md` を参照

## 開発セットアップ

### 前提条件

- Python 3.12
- Node.js 24+
- AWS CLI v2
- AWS SAM CLI v1.154+

### バックエンド

```bash
cd lambda
pip install -r requirements.txt
python -m pytest ../tests/unit/ -v
```

### フロントエンド

```bash
cd frontend
npm install
npm run dev      # 開発サーバー (localhost:5173)
npm run build    # ビルド
npm run test     # テスト
```

### E2Eテスト

```bash
cd tests/e2e
npx playwright install
npx playwright test
```

## ディレクトリ構成

```
image-analysis/
├── README.md
├── template.yaml          # 親スタック（ネスト）
├── api/
│   └── template.yaml      # APIスタック (SAM)
├── web/
│   └── template.yaml      # Webスタック (CloudFormation)
├── samconfig.toml         # SAMデプロイ設定（dev / production）
├── deploy.sh              # デプロイスクリプト
├── lambda/                # Lambda関数
│   ├── handler.py         # ハンドラ（解析・比較・通知連携）
│   ├── analyzer.py        # AI解析・比較ロジック（Bedrock Claude / Bedrock GPT / CPoA）
│   ├── notifier.py        # メール通知（SES）・LINE通知（Messaging API）
│   ├── rotation.py        # APIキーローテーション
│   └── requirements.txt
├── frontend/              # Vue3 SPA
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
├── tests/
│   ├── unit/              # Lambda単体テスト
│   ├── integration/       # API結合テスト
│   ├── e2e/               # Playwright E2E
│   └── security/          # セキュリティテスト
├── openapi/               # OpenAPIドキュメント
│   ├── openapi.yaml
│   ├── index.html
│   └── push.bat
├── scripts/               # ユーティリティスクリプト
└── Docments/              # 設計書・計画書
    ├── PLAN.md
    ├── DESIGN.md
    ├── API-DESIGN.md
    ├── API-SPEC.md
    ├── FRONTEND-DESIGN.md
    ├── INFRA-DESIGN.md
    ├── SECURITY-DESIGN.md
    ├── TEST-PLAN.md
    └── COST-ESTIMATE.md
```

## デプロイ手順

### 初回セットアップ（1回だけ）

```bash
# AWS CLIプロファイルを環境変数に設定（~/.bashrcに追記推奨）
export AWS_PROFILE=your_profile_name
```

- AI認証は Lambda 実行ロールの IAM/SigV4（Amazon Bedrock Claude / GPT / CPoA）で行うため、外部AIサービスのAPIキー登録は不要。Bedrockはモデルアクセスページが廃止されており、初回呼び出しで自動有効化される。
- LINE通知を使う場合のみ、チャネルアクセストークンをSSMに登録する:

```bash
aws ssm put-parameter \
  --name /image-analysis/line-channel-access-token \
  --type SecureString \
  --value YOUR_LINE_CHANNEL_ACCESS_TOKEN \
  --region ap-northeast-1
```

### デプロイ実行

```bash
# 依存インストール（初回のみ。フロントのビルドは deploy.sh が Amplify 設定生成後に実行するため手動ビルドしない）
cd frontend && npm install && cd ..

# 開発環境にデプロイ
bash deploy.sh dev

# 本番環境にデプロイ
bash deploy.sh prod
```

`deploy.sh` が自動的に以下を実行します:
1. SSMパラメータ存在確認
2. SAMビルド
3. ネストスタック一括デプロイ（API + Web）
4. Cognito設定ファイル自動生成（`frontend/src/amplifyconfiguration.ts`）
4b. フロントエンドビルド（Amplify設定生成**後**に実行 → dev/本番の設定混入による本番ログイン不能を防止）
5. S3同期・CloudFrontキャッシュ無効化

> フロントを事前に手動ビルドすると、別環境の Cognito 設定が本番バンドルへ混入し得るため、ビルドは deploy.sh（Step 4b）に任せる。

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| フロントエンド | Vue 3 + Vuetify 3 + Vite |
| 認証 | AWS Cognito + Amplify |
| API | API Gateway (REST) + Lambda (Python 3.12) |
| AI | Amazon Bedrock Claude / Amazon Bedrock GPT / Claude Platform on AWS（IAM/SigV4、既定 Bedrock Sonnet 5、APIキー不要） |
| 通知 | Amazon SES (DKIM検証済みドメイン) + LINE Messaging API |
| インフラ | CloudFront + S3 + Route53 + ACM |
| IaC | AWS SAM / CloudFormation |
| テスト | pytest（133件）+ Vitest（19件）+ Playwright |
