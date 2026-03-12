# テスト計画書

## テスト方針

- TDD（テスト駆動開発）で進める。テスト作成 → 失敗確認 → 実装の順序
- 単体テスト → 結合テスト → E2Eテスト → セキュリティテストの順に実施
- 画像データを含むテストはモックを使用し、外部API呼び出しを最小化

## テスト種別と構成

| 種別 | ツール | 対象 | ディレクトリ |
|------|--------|------|-------------|
| Lambda単体テスト | pytest | Python Lambda関数 | tests/unit/ |
| フロントエンド単体テスト | Vitest | Vue3コンポーネント | frontend/tests/ |
| API結合テスト | pytest + requests | API Gateway → Lambda | tests/integration/ |
| E2Eテスト | Playwright | ブラウザ操作全体 | tests/e2e/ |
| セキュリティテスト | pytest + curl | IP制限・認証 | tests/security/ |

## テストケース一覧

### Lambda単体テスト (pytest)

| ID | テストケース | 期待結果 |
|----|------------|---------|
| UT-01 | image指定で正常解析 | found/answer/confidence返却 |
| UT-02 | data指定で正常解析 | found/answer/confidence返却 |
| UT-03 | image/data両方未指定 | 400 MISSING_IMAGE |
| UT-04 | target未指定 | 400 MISSING_TARGET |
| UT-05 | 不正なbase64 | 400 INVALID_IMAGE |
| UT-06 | 20MB超の画像 | 400 IMAGE_TOO_LARGE |
| UT-07 | data URI形式のimage | 正常解析 (prefix除去) |
| UT-08 | model指定 (gpt-4.1) | 指定モデルで解析 |
| UT-09 | detail指定 (high) | high解像度で解析 |
| UT-10 | OpenAI API エラー時 | 500 AI_ERROR |
| UT-11 | healthエンドポイント | status: ok + timestamp |
| UT-12 | AIプロバイダー抽象化 | OpenAIAnalyzer正常動作 |
| UT-13 | S3キー参照で正常解析 | S3からimage取得→解析成功 |
| UT-14 | image_bucket未指定でimage_keyのみ | 400エラー |
| UT-15 | URL参照で正常解析 | URL取得→解析成功 |
| UT-16 | 不正ドメインのURL | 400エラー（ドメイン制限） |
| UT-17 | S3キーがimageより優先 | S3キー参照が使われる |

### フロントエンド単体テスト (Vitest)

| ID | テストケース | 期待結果 |
|----|------------|---------|
| FT-01 | ImageUploader: ファイル選択 | base64変換 + プレビュー表示 |
| FT-02 | ImageUploader: D&D | base64変換 + プレビュー表示 |
| FT-03 | AnalysisForm: 必須入力検証 | target空で送信不可 |
| FT-04 | ConfidenceChart: 0→N%アニメーション | SVG描画確認 |
| FT-05 | ChatLog: メッセージ追加 | ログ表示更新 |
| FT-06 | SecurityStatus: 項目表示 | 6項目すべて表示 |

### E2Eテスト (Playwright)

| ID | テストケース | 検証内容 |
|----|------------|---------|
| E2E-01 | ログイン/ログアウト | Cognito認証画面表示、セッション維持 |
| E2E-02 | 画像アップロード | ファイル選択、D&D、プレビュー |
| E2E-03 | 解析実行 (正常系) | ローディング → 結果表示 |
| E2E-04 | 解析実行 (異常系) | 画像なし/target空のエラー表示 |
| E2E-05 | レスポンス表示 | 確信度、トークン、レスポンスタイム |
| E2E-06 | 未認証アクセス | 401拒否 |
| E2E-07 | IP制限 | 403拒否 |

### セキュリティテスト

| ID | テストケース | 検証内容 |
|----|------------|---------|
| ST-01 | 許可IP外からのアクセス | 403 Forbidden |
| ST-02 | Origin Verifyなしの直接API呼出 | 403 Forbidden |
| ST-03 | 無効JWTでのAPI呼出 | 401 Unauthorized |
| ST-04 | 無効APIキーでのAPI呼出 | 403 Forbidden |
| ST-05 | APIキーなしでのワークフロー呼出 | 403 Forbidden |
| ST-06 | CORS不正オリジン | ブロック |

## テストディレクトリ構成

```
tests/
├── unit/
│   ├── test_handler.py          # Lambda ハンドラテスト
│   ├── test_analyzer.py         # AIプロバイダーテスト
│   └── conftest.py              # 共通フィクスチャ
├── integration/
│   └── test_api.py              # API結合テスト
├── e2e/
│   ├── playwright.config.ts
│   ├── fixtures/
│   │   ├── test-image-bear.jpg
│   │   ├── test-image-empty.jpg
│   │   └── auth.setup.ts
│   └── specs/
│       ├── auth.spec.ts
│       ├── upload.spec.ts
│       ├── analyze.spec.ts
│       └── security.spec.ts
└── security/
    └── test_security.py
frontend/
└── tests/
    ├── ImageUploader.spec.ts
    ├── AnalysisForm.spec.ts
    ├── ConfidenceChart.spec.ts
    └── ChatLog.spec.ts
```

## テスト実行手順

```bash
# Lambda単体テスト
cd tests && python -m pytest unit/ -v

# フロントエンド単体テスト
cd frontend && npm run test

# E2Eテスト
cd tests/e2e && npx playwright test

# セキュリティテスト (デプロイ後)
cd tests && python -m pytest security/ -v

# 全テスト実行
python -m pytest tests/ -v && cd frontend && npm run test
```

## 合格基準

| 種別 | 基準 |
|------|------|
| Lambda単体テスト | 全テストパス、カバレッジ80%以上 |
| フロントエンド単体テスト | 全テストパス |
| E2Eテスト | 全シナリオパス |
| セキュリティテスト | 全テストパス (不正アクセス拒否確認) |
| 総合 | 全種別パスで合格 |
