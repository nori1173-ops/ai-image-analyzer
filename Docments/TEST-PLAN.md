# テスト計画書

## テスト方針

- TDD（テスト駆動開発）で進める。テスト作成 → 失敗確認 → 実装の順序
- 単体テスト → 結合テスト → E2Eテスト → セキュリティテストの順に実施
- 画像データを含むテストはモックを使用し、外部API呼び出しを最小化

## テスト種別と構成

| 種別 | ツール | 対象 | ディレクトリ |
|------|--------|------|-------------|
| Lambda単体テスト | pytest | Python Lambda関数 | tests/unit/ |
| フロントエンド単体テスト | Vitest | Vue3コンポーネント・ユーティリティ | frontend/src/__tests__/ ・ components/__tests__/ |
| API結合テスト | pytest + requests | API Gateway → Lambda | tests/integration/ |
| E2Eテスト | Playwright | ブラウザ操作全体 | tests/e2e/ |
| セキュリティテスト | pytest + curl | IP制限・認証 | tests/security/ |

## テストケース一覧

### Lambda単体テスト構成（pytest 133件）

| テストファイル | 件数 | 対象 |
|--------------|------|------|
| test_handler.py | 32 | ハンドラ（モデル名前空間ルーティング・オリジン検証・解析/比較の入力検証・effort検証・通知連携） |
| test_rotation.py | 14 | API Gateway キーローテーション（4ステップ） |
| test_analyzer.py | 30 | AI推論（Bedrock Claude / Bedrock GPT / CPoAのルーティング、リージョン、media_type判定、analyze/compare、detail無視、effort連携） |
| test_notifier.py | 15 | 通知モジュール（SESNotifier To/CC/BCC・BCCヘッダ非掲載、LINENotifier、未構成スキップ） |
| test_compare.py | 42 | 画像比較API（before_/after_ 4方式、perspective検証、モデル名前空間検証、notify分岐、宛先To/CC/BCC検証、LINE通知、危険時通知） |
| **合計** | **133** | `pytest tests/unit/ -v`（パラメトライズ展開込みの収集件数） |

### Lambda単体テスト（画像解析）

| ID | テストケース | 期待結果 |
|----|------------|---------|
| UT-01 | image指定で正常解析 | found/answer/confidence返却 |
| UT-02 | data指定で正常解析 | found/answer/confidence返却 |
| UT-03 | image/data両方未指定 | 400 MISSING_IMAGE |
| UT-04 | target未指定 | 400 MISSING_TARGET |
| UT-05 | 不正なbase64 | 400 INVALID_IMAGE |
| UT-06 | 20MB超の画像 | 400 IMAGE_TOO_LARGE |
| UT-07 | data URI形式のimage | 正常解析 (prefix除去) |
| UT-08 | model指定 (anthropic.claude-sonnet-5) | 指定モデルで解析 |
| UT-09 | detail指定（廃止パラメータ） | 送信されても無視・正常解析 |
| UT-10 | AI API エラー時 | 500 AI_ERROR |
| UT-11 | healthエンドポイント | status: ok + timestamp |
| UT-12 | AI推論抽象化 | ClaudeAnalyzer正常動作 |
| UT-13 | S3キー参照で正常解析 | S3からimage取得→解析成功 |
| UT-14 | image_bucket未指定でimage_keyのみ | 400エラー |
| UT-15 | URL参照で正常解析 | URL取得→解析成功 |
| UT-16 | 不正ドメインのURL | 400エラー（ドメイン制限） |
| UT-17 | S3キーがimageより優先 | S3キー参照が使われる |
| UT-18 | 不正なmodel名（gpt* 等 claude以外） | 400 Invalid model |
| UT-19 | 許可リスト外バケット指定 | 400（バケット不許可） |
| UT-20 | オリジン検証失敗（直接アクセス） | 403 Forbidden |

### Lambda単体テスト（AI推論: test_analyzer.py）

| ID | テストケース | 期待結果 |
|----|------------|---------|
| AN-01 | model 振り分け（Claudeのみ） | claude*→ClaudeAnalyzer、既定/省略時も Claude Haiku |
| AN-02 | media_type自動判定 | PNG(iVBOR)→image/png、それ以外→image/jpeg |
| AN-03 | detail引数 | 渡されても無視される（廃止パラメータ） |
| AN-04 | Claude analyze/compare | tool_use強制で構造化出力を返却 |
| AN-05 | effort指定（Claude） | output_config.effort に連携 |
| AN-06 | effort省略 | output_config を付与しない |

### Lambda単体テスト（画像比較: test_compare.py）

| ID | テストケース | 期待結果 |
|----|------------|---------|
| CMP-01 | before/after 2枚指定で正常比較 | danger/risk_level/reason/changes返却 |
| CMP-02 | before_/after_ の4方式（image/data/url/bucket+key） | 各方式で画像取得成功 |
| CMP-03 | perspective未指定 | 400 perspective is required |
| CMP-04 | before/after いずれか欠落 | 400（画像必須） |
| CMP-05 | notify=true かつ danger=true | メール送信・notified=true・message_id付与 |
| CMP-06 | notify=true かつ danger=false | メール送信せず・notified=false |
| CMP-07 | 通知送信失敗 | 200維持・notify_error格納 |
| CMP-08 | notify_to/notify_cc/notify_bcc 指定 | 指定宛先へ送信（To省略時はサーバー既定） |
| CMP-09 | 不正な notify_to/cc/bcc（非配列/非メール/10件超） | 400 Invalid notify_* |
| CMP-10 | notify_line=true かつ danger=true | S3保存→presigned URL→LINE push・line_notified=true |
| CMP-11 | LINE未構成（トークン/宛先なし） | スキップ・line_skip_reason格納 |
| CMP-12 | LINE送信失敗 | 200維持・line_error格納 |

### Lambda単体テスト（通知: test_notifier.py）

| ID | テストケース | 期待結果 |
|----|------------|---------|
| NT-01 | SESNotifier 添付付き送信 | send_raw_email呼び出し・message_id返却 |
| NT-02 | 送信元未設定 | ValueError（SES_SENDER） |
| NT-03 | 通知先未設定 | ValueError（NOTIFY_RECIPIENTS） |
| NT-04 | 複数宛先（カンマ区切り） | 全宛先へ送信 |
| NT-05 | To/CC/BCC 指定送信 | Destinations に To+CC+BCC、Cc はヘッダに掲載・Bcc はヘッダ非掲載 |
| NT-06 | To省略 | サーバー既定（recipients）へ送信 |
| NT-07 | LINENotifier push | LINE Messaging API へ text + image2枚を送信 |
| NT-08 | LINE未構成（LINE_NOTIFY_TO / トークン欠落） | LineNotConfiguredError |

### フロントエンド単体テスト (Vitest)

実装済みの vitest テスト（合計19件、`frontend/src/__tests__/` ・ `frontend/src/components/__tests__/`）。以下は主なテストケース。

| ファイル | ID | テストケース | 期待結果 |
|---------|----|------------|---------|
| App.spec.ts | FT-01 | App: レンダリング | クラッシュせず描画 |
| notifications.spec.ts | FT-02 | parseRecipientList: カンマ区切り | trim・空要素除去した配列 |
| notifications.spec.ts | FT-03 | parseRecipientList: 空文字 | 空配列 |
| ImageLightbox.spec.ts | FT-04 | ImageLightbox: 表示 | title・画像を表示 |
| ImageLightbox.spec.ts | FT-05 | ImageLightbox: 閉じるボタン | update:modelValue=false を発火 |
| ImageLightbox.spec.ts | FT-06 | ImageLightbox: オーバーレイclose | close イベント転送 |
| models.spec.ts | FT-07 | モデル一覧・賢さ（目安） | 12モデル、0.5点刻みの `intelligence` を検証 |
| CostPanel.spec.ts | FT-08 | CostPanel: 賢さ・単価・監視コスト | 半星評価、`x/10`表示、コスト注記を検証 |
| PlatformInfoDialog.spec.ts | FT-09 | プラットフォーム説明 | ヘルプボタンで説明ダイアログを表示 |

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
│   ├── test_handler.py          # Lambda ハンドラテスト（30件）
│   ├── test_rotation.py         # API Gateway キーローテーション（14件）
│   ├── test_analyzer.py         # AI推論テスト（Claudeのみ・15件）
│   ├── test_notifier.py         # 通知モジュール（15件）
│   ├── test_compare.py          # 画像比較API（41件）
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
└── src/
    ├── __tests__/
    │   ├── App.spec.ts
    │   └── notifications.spec.ts
    └── components/__tests__/
        └── ImageLightbox.spec.ts
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
| Lambda単体テスト | 全133件パス、カバレッジ80%以上 |
| フロントエンド単体テスト | 全テストパス（vitest 19件） |
| E2Eテスト | 全シナリオパス |
| セキュリティテスト | 全テストパス (不正アクセス拒否確認) |
| 総合 | 全種別パスで合格 |
