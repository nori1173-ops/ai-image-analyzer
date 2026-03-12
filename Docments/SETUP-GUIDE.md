# セットアップガイド

本プロジェクトをデプロイするために変更が必要な設定値の一覧です。

## 1. AWSアカウント・インフラ設定

| ファイル | 設定項目 | 現在のプレースホルダー | 設定すべき値 |
|---------|---------|---------------------|------------|
| `samconfig.toml` | Lambda Layer ARN | `arn:aws:lambda:ap-northeast-1:123456789012:layer:PowertoolsPython:74` | 自分のAWSアカウントにデプロイ済みのPowertools Layerの ARN |
| `web/template.yaml` | ドメイン名 | `example-cloud.com` | Route53で管理する独自ドメイン名 |
| `web/template.yaml` | Hosted Zone ID | `ZXXXXXXXXXXXXX` | Route53のHosted Zone ID |
| `web/template.yaml` | ACM証明書ARN | `arn:aws:acm:us-east-1:123456789012:certificate/xxxxxxxx-...` | us-east-1リージョンで発行したACM証明書のARN |
| `web/template.yaml` | 許可IPアドレス | `203.0.113.1` | アクセスを許可するグローバルIPアドレス |
| `web/template.yaml` | Origin Verify値 | `your-origin-verify-secret` | CloudFront→API Gateway間の検証用シークレット文字列（任意の値） |
| `api/template.yaml` | Origin Verify値 | `your-origin-verify-secret` | 上記と同じ値を設定 |

## 2. SSM Parameter Store

デプロイ後にAWS Systems Manager Parameter Storeに以下のパラメータを手動作成する必要があります。

| パラメータパス | 種類 | 値 |
|--------------|------|-----|
| `/image-analysis/openai-api-key` | SecureString | OpenAI APIキー |

## 3. Cognito ユーザー作成

デプロイ後、Cognitoユーザープールでユーザーを手動作成します（`AdminCreateUserOnly: true`のため）。

```bash
aws cognito-idp admin-create-user \
  --user-pool-id <UserPoolId> \
  --username <メールアドレス> \
  --user-attributes Name=email,Value=<メールアドレス>
```

## 4. フロントエンド設定

| ファイル | 設定項目 | 説明 |
|---------|---------|------|
| `frontend/src/amplifyconfiguration.ts` | Amplify設定 | `.gitignore`で除外済み。デプロイ後のCognito情報で生成する |

Amplify設定ファイルの生成例：

```typescript
const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: '<CognitoUserPoolId>',
      userPoolClientId: '<CognitoUserPoolClientId>',
    }
  }
};
export default amplifyConfig;
```

## 5. スクリプト設定

| ファイル | 設定項目 | 現在のプレースホルダー | 設定すべき値 |
|---------|---------|---------------------|------------|
| `scripts/apply_api_policy.sh` | AWSプロファイル | `your-profile` | AWS CLIのプロファイル名 |
| `openapi/push.bat` | S3バケットURL | `s3://openapi.example-cloud.com/image-analysis` | OpenAPI仕様を公開するS3バケットのURL |

## 6. 環境変数（Lambda）

CloudFormationテンプレートで自動設定されるため、手動設定は不要です。参考情報：

| 環境変数 | 設定元 | 用途 |
|---------|-------|------|
| `ORIGIN_VERIFY_HEADER` | `api/template.yaml` パラメータ | CloudFrontオリジン検証ヘッダー名 |
| `ORIGIN_VERIFY_VALUE` | `api/template.yaml` パラメータ | CloudFrontオリジン検証値 |
| `SSM_OPENAI_API_KEY_PATH` | `api/template.yaml` ハードコード | OpenAI APIキーのSSMパス |
| `LogLevel` | `samconfig.toml` パラメータ | ログレベル（DEBUG/INFO/WARNING/ERROR） |

## デプロイ手順

```bash
# 1. フロントエンドビルド
cd frontend && npm install && npm run build && cd ..

# 2. SAMビルド＆デプロイ（開発環境）
sam build && sam deploy

# 3. SAMビルド＆デプロイ（本番環境）
sam build && sam deploy --config-env production

# 4. フロントエンドをS3にアップロード
aws s3 sync frontend/dist/ s3://<WebsiteBucketName>/ --delete

# 5. CloudFrontキャッシュ無効化
aws cloudfront create-invalidation --distribution-id <DistributionId> --paths "/*"
```
