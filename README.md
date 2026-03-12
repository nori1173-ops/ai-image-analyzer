# 画像解析API (Image Analysis)

画像に対して、指定オブジェクト（人物、車両、損傷等）の有無をAIで判定するAPI。

> **初めてデプロイする方へ**: プレースホルダー値（ドメイン名・AWSアカウントID等）の設定が必要です。
> **[セットアップガイド (Docments/SETUP-GUIDE.md)](Docments/SETUP-GUIDE.md)** を参照してください。

## テスト画面

| 項目 | 値 |
|------|-----|
| URL | https://image-analysis.example-cloud.com |
| アクセス条件 | 許可IPからのみ |
| 認証 | Cognito (メール/パスワード) |
| ユーザーID | demouser |
| パスワード | DemoPass123 |

## 利用手順

1. https://image-analysis.example-cloud.com にアクセス
2. メールアドレス・パスワードでログイン
3. 画像をドラッグ&ドロップまたはクリックでアップロード
4. 「見つけたいもの」にテキスト入力（例: 人物、車両）
5. 必要に応じてモデル・解像度を選択
6. 「解析する」ボタンをクリック
7. 結果（発見有無・確信度・AI回答）を確認

## API直接呼び出し

### curl (Cognito JWT認証)

```bash
IMAGE_B64=$(base64 -w 0 photo.jpg)
curl -X POST https://image-analysis.example-cloud.com/api/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $COGNITO_TOKEN" \
  -d "{\"image\": \"data:image/jpeg;base64,$IMAGE_B64\", \"target\": \"crack\"}"
```

### curl (APIキー認証 - ワークフロー用)

```bash
curl -X POST https://<api-gateway-domain>/prod/workflow/analyze \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d "{\"data\": \"$(base64 -w 0 photo.jpg)\", \"target\": \"crack\"}"
```

### ヘルスチェック

```bash
curl https://image-analysis.example-cloud.com/api/health
```

## ワークフロー連携

external-systemの `UploadByHttp` タスクから呼び出し可能。プログラム修正不要。

1. SNSトピックでメール受信を検知
2. メッセージ取得 → 添付判定 → HTTP送信 の順で処理
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
│   ├── handler.py         # ハンドラ
│   ├── analyzer.py        # AI解析ロジック
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

# OpenAI APIキーをSSMパラメータに登録
aws ssm put-parameter \
  --name /image-analysis/openai-api-key \
  --type SecureString \
  --value YOUR_OPENAI_API_KEY \
  --region ap-northeast-1
```

### デプロイ実行

```bash
# フロントエンドビルド
cd frontend && npm install && npm run build && cd ..

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
5. S3同期・CloudFrontキャッシュ無効化

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| フロントエンド | Vue 3 + Vuetify 3 + Vite |
| 認証 | AWS Cognito + Amplify |
| API | API Gateway (REST) + Lambda (Python 3.12) |
| AI | OpenAI Vision API (GPT-4.1-mini / 4.1 / 5.2) |
| インフラ | CloudFront + S3 + Route53 + ACM |
| IaC | AWS SAM / CloudFormation |
| テスト | pytest + Vitest + Playwright |
