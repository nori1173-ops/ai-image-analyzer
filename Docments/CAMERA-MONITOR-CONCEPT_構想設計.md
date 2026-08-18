# カメラ監視設定 UI (camera-monitor) 構想設計

| 項目 | 内容 |
|------|------|
| ドキュメント名 | CAMERA-MONITOR-CONCEPT_構想設計.md |
| バージョン | v0.5 (構想段階、基本設計への昇格前) |
| 作成日 | 2026-07-14 |
| 作成者 | 弊社 開発部 |
| 関連チケット | redmine-dev #4658 (本件)、#4656 (Bedrock対応)、#4018 (LINE連携検討)、redmine-cs #2827 (SSO基盤)、#2824 (SSOリンクボタン前例) |
| UI 名 (仮) | `camera-monitor` (SSO 命名規約: `sso-ui-handler-camera-monitor`) |
| 実装先 | example-portal リポジトリ (SSO UI追加パターン)。本書は先行して image-analysis リポジトリに置く |

> **本書の位置づけ**: image-analysis API の商品化動線として、連携元SaaS_A の地点 (カメラ機器) から SSO で監視設定を行い、カメラ画像の着信を裏で監視して危険時にメール通知する機能の構想を記録する。画面設計・DB設計を主とし、着信フックは mail-backend 既存の DeliverTopic (SNS) 購読に決定済み (§6、経緯は CAMERA-MONITOR-HOOK-COMPARISON_フック方式比較.md)。

---

## 1. 目的・背景

- image-analysis API (Bedrock/CPoA 12モデル対応済み、#4656) は現状テスト画面と汎用APIのみで、**顧客が使うための動線が存在しない**
- 販売動線は 2 本に整理する (2026-07-14 協議):
  1. **ワークフロー版 (軽量)**: 連携元SaaS_A 不要の顧客 (カメラ + 判定 + 危険時通知だけ欲しい) の受け皿。mail-backend ワークフローからコア API を M2M 利用
  2. **連携元SaaS_A オプション版 (本書)**: 地点登録 → SSO リンクで設定 → 着信監視 → メール通知
- 連携元SaaS_A に乗せるのは**表面 (設定 UI・履歴表示) のみ**。設定は機器番号 (spot_code) をキーに弊社 DB へ保存し、実行はバックエンドの画像着信監視が担う
- 判定エンジンは既存 image-analysis API (`/compare`) をそのまま使う。モデル選択・コスト表示・通知宛先仕様 (#4654/#4656 実装) を UI 部品ごと再利用する

### 1.1 本 UI の位置付け

- **設定 + 閲覧のみの薄い UI**。カメラ・通信機への働きかけは一切しない (point-setup の読み取り専用原則より更に軽い)
- 連携元SaaS_A への書き込みもない (設定は弊社 DB のみ)。したがって **point-setup の最大論点だった 連携元SaaS_A 管理 API トークン (#2815) が不要**で、ベンダー依頼はリンクボタン 1 点に収まる
- 判定履歴 (危険度・理由・差分写真) を確認できる**再訪価値のある画面**とし、オプション商品として顧客の目に見える顔を担う

## 2. 全体フロー

```
連携元SaaS_A 地点 (カメラ機器) 詳細画面 (ベンダーがリンクボタン追加)
  → SSO (既存基盤、sso-ui-handler-camera-monitor を新設、relay 無改修)
  → 弊社 SPA: モデル・監視観点・通知先メールを設定 → 設定DB保存 (spot_code キー)
  ---- 以後は自動 ----
カメラ → メール添付 → mail-backend → (example-powertools-python で JSON/Base64 化)
  → transfer-server.1 → 連携元SaaS_A
       └ [着信フック §6] → ingest → 設定DB照会 → 前回画像と /compare 判定
                                → 判定履歴DB + 画像S3 保存
                                → danger かつ 閾値以上 → SES メール通知 (To/CC/BCC)
```

## 3. 構成・責務分離

| 領域 | 主体 | 内容 |
|---|---|---|
| 連携元SaaS_A | ベンダー | 地点詳細画面にリンクボタン追加のみ (#2824 同型の SSO 発射台) |
| SSO 基盤 | example-portal (既存) | relay 無改修。SSM `allowed_uis` に `camera-monitor` 追加 |
| camera-monitor UI | example-portal (新規) | `sso-ui-handler-camera-monitor` + SPA + UI 専用バックエンド (設定 CRUD / 履歴読み出しのプロキシ Lambda) |
| 監視設定 DB / 判定履歴 DB / 画像 S3 | example-portal (新規) | §5。ingest と UI の共有ストア |
| 着信フック + ingest | example-portal (新規) | DeliverTopic (SNS) 購読で画像着信を検知し ingest 処理を起動 (§6) |
| 判定エンジン | image-analysis (既存) | `/workflow/compare` (API キー、#4400 ローテーション対応済み) を M2M 呼び出し。モデル・監視観点・通知宛先仕様は既存 API のまま |
| メール通知 | image-analysis (既存) | `/compare` の notify 機能 (SES、To/CC/BCC 各10件) をそのまま利用 |

> 通知を image-analysis 側 (compare の notify) に残すか、ingest 側で独立実行するかは基本設計で確定する。第 1 案は「compare 呼び出し時に notify_to 等を渡すだけ」の既存機能フル活用 (追加実装ゼロ)。

## 4. SSO 契約 (ui-lte-m 同型)

現行契約 (JWT-SSO-DESIGN §8.3) の**機器コンテキスト UI そのまま**であり、契約拡張は不要。

| 項目 | 扱い |
|---|---|
| `spot_code` | 必須 (設定 DB の主キー)。**カメラは NetA 配下にのみ存在** (mail-backend は NetA 専用、2026-07-14 確認) のため、常に 3 要素の地点 CD `通信機アカウント-NetAアドレス-機器型番` で確定 (LTE-M の 2 要素例外は本 UI に無関係) |
| `tenant_id` / `site_code` / `spot_name` | 表示・保存 (認可判定には使わない、粗い認可方針 §6.1 準拠) |
| 連携元SaaS_A 管理 API トークン | **不要** (連携元SaaS_A への書き込みなし) |
| 機器隔離 | ui-lte-m と同じく SPA 側 spot_code 照合 + UI 専用バックエンドで spot_code スコープ強制 |

- SSM 発信元マスターの `allowed_uis` に `camera-monitor` を追加 (連携元SaaS_A / sso-mock)
- dev 検証は sso-mock コンソールに camera-monitor 向け POST を追加 (point-setup と同じモックファースト)

## 5. 画面設計 (主成果物 1/2)

### 5.1 ワイヤーフレーム

タブ 2 枚構成。ヘッダに SSO 業務情報 (テナント / 現場 / 地点名) を表示する。

```
┌ カメラ監視設定 ─ ○○市 / △△現場 / 水位観測所A (sc00000001-02-CAM-1) ──┐
│ [ 設定 ] [ 判定履歴 ]                                                  │
├────────────────────────────────────────────────────────────────────────┤
│ 監視         ( ● 有効   ○ 無効 )                                      │
│ モデル       [ Claude Sonnet 5（推奨） ▾ ]  (?)                        │
│   └ コストパネル: 単価 / 1回 / 10分間隔監視 / 1時間間隔監視 ($・¥)     │
│                   賢さ（目安）★★★★☆ 8.5/10                            │
│ 監視観点     [ 河川の増水・氾濫の予兆を監視                        ]   │
│              (プリセット: 土砂災害 / 河川増水 / 積雪 / 自由入力)       │
│ 通知条件     [ 危険度 low 以上で通知 ▾ ]   (low / medium / high)       │
│ 通知先 To    [ bousai@example.jp, field@example.jp                 ]   │
│        CC    [                                                     ]   │
│        BCC   [                                                     ]   │
│                                                                        │
│ [ テスト通知を送信 ]                                   [ 保存 ]        │
└────────────────────────────────────────────────────────────────────────┘

[判定履歴] タブ:
│ 07-14 10:20  危険度: high   増水により護岸が冠水…   [前回|今回] 📧済 │
│ 07-14 10:10  危険度: none   有意な変化なし           [前回|今回]      │
│ (サムネイルクリックで拡大 = ImageLightbox 流用、presigned URL 表示)   │
```

### 5.2 設定項目定義

| 項目 | 型 / 制約 | 既定値 | 備考 |
|---|---|---|---|
| 監視 有効/無効 | boolean | 無効 | 保存済み設定があっても無効化で ingest はスキップ |
| モデル | 12 モデル (frontend/src/models.ts と同一) | `anthropic.claude-sonnet-5` | Bedrock/CPoA グループコンボ + ? ダイアログ + コストパネルを流用 |
| 監視観点 | 文字列 (1〜200 字) | — | `/compare` の perspective に渡す。プリセット + 自由入力 |
| 通知条件 (最低危険度) | enum: low / medium / high | low | danger=true かつ risk_level が閾値以上で通知 |
| 通知先 To / CC / BCC | メール配列、各最大 10 件・合計 50 件以内 | — | `/compare` の notify_to/cc/bcc 仕様 (#4654) と同一。To は 1 件以上必須 |

### 5.3 再利用する既存部品 (image-analysis frontend、Vuetify3)

| 部品 | 用途 |
|---|---|
| `models.ts` | 12 モデル定義・単価・賢さ・為替・コスト計算 (`estimateCost`) |
| `CostPanel.vue` | モデル選択時のコスト + 賢さ表示 (監視頻度はカメラ側送信間隔を入力して試算) |
| `PlatformInfoDialog.vue` | Bedrock / CPoA の違い説明 (? ボタン) |
| `ImageLightbox.vue` | 履歴サムネイルの拡大表示 |
| 宛先バリデーション | To/CC/BCC カンマ区切り入力・件数上限・形式チェック |

- デザインは 連携元SaaS_A 準拠 (ui-lte-m / sso-mock の踏襲)。日本語フォントスタック明示 (中華フォント禁止ルール)
- テスト通知: 保存済み設定で SES 送信のみ実行する軽い動線 (判定は行わない)。宛先誤り検知用

## 6. 実行系: 着信フックと ingest

### 6.1 ingest インターフェース (縫い目)

フック位置がどこに決まっても下流を変えないよう、着信は 1 インターフェースに隠蔽する:

```
ingest(spot_code, image_base64, timestamp)
  1. 設定 DB を spot_code で照会 → 無し or 無効 → 終了 (ログのみ)
  2. S3 latest/{spot_code}.jpg を取得 → 無し (初回) → latest 保存のみで終了
  3. image-analysis /workflow/compare を呼出 (model, perspective, 前回画像, 今回画像,
     notify_to/cc/bcc は通知条件を満たす場合のみ付与)
  4. 判定履歴 DB へ保存 + latest を今回画像で差し替え + 履歴画像を S3 保存
  5. 通知結果 (message_id / スキップ理由) を履歴に記録
```

- 多重着信・順序逆転ガード: timestamp が latest の取得時刻より古い場合はスキップ。同一 spot_code の同時実行は DynamoDB 条件付き書き込みで排他
- 通知判定: danger=true かつ risk_level ≥ notify_min_risk のときのみ notify を付けて呼び出す (compare 自体は毎回実行し履歴を残す)

### 6.2 フック位置: 案 A-3 (DeliverTopic (SNS) 購読) を採用 (2026-07-16 変更決定)

カメラ画像の経路: カメラ → メール添付 → mail-backend → example-powertools-python で JSON/Base64 化 → transfer-server.1 → 連携元SaaS_A。

| 案 | 内容 | 利点 | 課題 |
|---|---|---|---|
| A: mail-backend 受信処理 | 画像メール保存時に ingest を呼ぶ (SQS/直接) | 最短経路・確実・リアルタイム。ワークフロー版とも共通化しやすい | mail-backend 改修が必要 (受信パスへの責務追加) |
| B: transfer-server.1 送信経路 | 連携元SaaS_A への送信時に分岐して ingest へも渡す | JSON/Base64 変換済みデータを再利用できる。連携元SaaS_A に届くものと同一 | transfer 改修。連携元SaaS_A 非連携の顧客 (ワークフロー版) の画像が通らない可能性 |
| C: CloudWatch 経由 | 受信ログ/イベントを購読して検知 | 既存システム完全無改修 | ログに画像本体が無ければ結局取得 API が必要。遅延・欠落リスク、ログ形式への依存 |

> **2026-07-14 一次決定**: mail-backend の受信実装を実ソース確認 (SES → S3 `inbox/{message_id}` → SNS → Subscriber) した上で案 A 系を 3 方式 (A-0: S3 EventBridge 購読 / A-1: Subscriber 改修でイベント発行 / A-2: NetaMailTable DynamoDB Streams) に詳細化して比較し、A-0 を一次採用した。
>
> **2026-07-16 変更決定**: A-0 は mail-backend 管理側より「受信バケットの設定変更は不可」との回答を受け不成立。代わりに先方から提示された**案 A-3 = 既存 DeliverTopic (SNS メール配信トピック) の購読を採用**した。DeliverTopic は Subscriber が配信の都度 publish している拡張システム向けの既設の口で、メッセージにはメール ID を含む永続保存先キー (`accounts/{アカウント}/messages/{メールID}`) が入り、解析ライブラリ (mail_backend Library / example-powertools-python) もコードベースに既存。こちらは購読を 1 本追加するだけで、**mail-backend 側はコード・設定とも変更ゼロ**。アーキ図・かみ砕き説明・コスト試算 (月 100 万通 ≈ $0.6) は CAMERA-MONITOR-HOOK-COMPARISON_フック方式比較.md v1.1 を参照。

## 7. DB 設計 (主成果物 2/2)

DynamoDB オンデマンド 2 テーブル + S3 1 バケット。example-portal 側スタック (camera-monitor app) に置く。

### 7.1 監視設定テーブル `camera-monitor-settings`

| 属性 | 型 | 内容 |
|---|---|---|
| `spot_code` (PK) | S | 機器一意キー = 連携元SaaS_A 地点 CD `通信機アカウント-NetAアドレス-機器型番` (例: `sc00000001-02-CAM-1`) |
| `enabled` | BOOL | 監視有効フラグ |
| `model` | S | 判定モデル ID (既定 `anthropic.claude-sonnet-5`) |
| `perspective` | S | 監視観点 |
| `notify_to` / `notify_cc` / `notify_bcc` | L\<S\> | 通知宛先 (各最大 10 件) |
| `notify_min_risk` | S | 通知する最低危険度 (low / medium / high) |
| `tenant_id` / `site_code` / `spot_name` | S | SSO POST 由来の表示情報 (認可判定には使わない) |
| `created_at` / `created_by` / `updated_at` / `updated_by` | S | by = SSO JWT の sub (操作者追跡) |
| `schema_version` | N | 将来のスキーマ移行用 |

### 7.2 判定履歴テーブル `camera-monitor-results`

| 属性 | 型 | 内容 |
|---|---|---|
| `spot_code` (PK) | S | 機器一意キー |
| `timestamp` (SK) | S | 判定時刻 (ISO 8601) |
| `danger` / `risk_level` | BOOL / S | 判定結果 (`/compare` レスポンスそのまま) |
| `reason` / `changes` | S | 判定理由・検出変化 |
| `model` | S | 実際に使用したモデル ID |
| `usage` | M | prompt / completion / total トークン (コスト実測用) |
| `image_before_key` / `image_after_key` | S | S3 オブジェクトキー |
| `notified` | BOOL | メール送信有無 |
| `notify_detail` | S | message_id またはスキップ理由 |
| `ttl` | N | 90 日で自動削除 (DynamoDB TTL) |

- 将来ウィジェット (§9) やテナント横断一覧が必要になったら GSI `tenant_id`-`timestamp` を追加する (当面不要)

### 7.3 画像 S3 バケット `camera-monitor-images`

| プレフィックス | 内容 | ライフサイクル |
|---|---|---|
| `latest/{spot_code}.jpg` | 前回画像 (比較用、着信ごとに上書き) | なし |
| `results/{spot_code}/{timestamp}-before.jpg` / `-after.jpg` | 判定履歴の画像 | 90 日で自動削除 (履歴 TTL と揃える) |

- 非公開・SSE-AES256。履歴画面・通知メールは presigned URL で参照 (image-analysis の LineImagesBucket と同型)

## 8. コスト概算 (参考)

- インフラ追加分: DynamoDB オンデマンド + S3 で月数十円〜数百円オーダー (画像 200KB × 4,320 回/月 ≒ 0.9GB/月/カメラ)
- 判定コストが支配的: 既定 Bedrock Sonnet 5 で 10 分間隔 ≒ $42/月/カメラ、1 時間間隔 ≒ $7/月/カメラ (Docments/COST-ESTIMATE.md 参照)。カメラの送信間隔に依存し、設定画面のコストパネルで顧客に事前提示する

## 9. 将来構想 (本書では設計しない)

| 構想 | 内容 |
|---|---|
| IFRAME ウィジェット | 連携元SaaS_A の「他 WEB コンテンツウィジェット (IFRAME)」に SSO 対応の差分写真ビューを提供 (最新の前回/今回ペア + 危険度 + 理由)。判定履歴 DB + S3 画像を表示するだけの読み取り専用 SPA。heatmap-component の親子 iframe + トークン受け渡しの型を再利用 |
| LINE 通知 | mail-backend #4018 のワークフロー LINE 配信ノード (顧客がチャネルトークンを登録する方針) に委譲する。または将来、設定画面にチャネルトークン登録欄を追加して image-analysis 実装済みの LINE push を有効化する |
| ワークフロー版 (軽量顧客) | 同じ設定 DB / ingest を使い、設定登録は弊社代行 (受注時)。通知はワークフローに委譲するかそのまま SES を使う。フックが受信経路起点 (A-3) のため 連携元SaaS_A 連携の有無に関わらず同一経路で成立する |

## 10. 論点・未確定事項

| # | 論点 | 現時点の考え |
|---|---|---|
| 1 | 着信フックの位置 | **決定済み (2026-07-16 変更)**: 案 A-3 = 既存 DeliverTopic (SNS) の購読。一次決定の A-0 (S3 EventBridge) は受信バケットの設定変更不可の回答により不成立 (詳細は CAMERA-MONITOR-HOOK-COMPARISON_フック方式比較.md) |
| 2 | カメラ機器の 連携元SaaS_A 登録実態 | カメラの機器型番と spot_code の実例、画像メール (通信機アカウント + NetA アドレス) から spot_code への対応付け方法を確認。書式は 3 要素で確定 (カメラは NetA 配下のみ) |
| 3 | ingest → image-analysis の認証 | 第 1 案: 既存 `/workflow/compare` + API キー (#4400 ローテーション対応済み)。Cognito Client Credentials (パターン D) への移行は将来判断 |
| 4 | オプション契約管理 | SSM `allowed_uis` は発信元単位でテナント単位ではない。未契約テナントの遮断をどこで行うか (当面: 契約テナントのみにリンクボタンを出す運用 / 将来: settings 登録時にテナント許可リスト照合) |
| 5 | 通知メールの送信元 | image-analysis の SES (example-cloud.com、DKIM 検証済み) を流用する想定。送信枠・レピュテーションの確認 |
| 6 | 初回着信の扱い | 前回画像が無いため判定せず latest 保存のみ (§6.1)。「監視開始直後の 1 回は判定なし」を画面に注記 |
| 7 | SES サンドボックス/宛先制限 | 顧客宛先への送信となるため、送信ポリシー (ドメイン制限なし、#4654 の判断踏襲) を再確認 |
| 8 | DeliverTopic 購読の実装条件 | camera-monitor 側からの購読可否 (同一 AWS アカウントなら追加設定不要 / クロスアカウントならトピックポリシーへの購読許可を先方に依頼)、mail_backend Library・example-powertools-python レイヤの利用方法を実装前に確認 |

## 11. 開発計画 (モックファースト、point-setup 踏襲)

ベンダー回答・フック協議と無関係に着手できる部分から進める:

1. sso-mock コンソールに camera-monitor 向け POST (機器コンテキスト契約) を追加し、SSO 発射台を先行検証
2. example-portal に `ui-camera-monitor` app 新設: SPA (設定 + 履歴) + UI 専用バックエンド + settings/results/S3
3. ingest をスタブ起動 (手動 POST で疑似着信) し、`/workflow/compare` 結線・判定履歴・通知まで E2E
4. フック本実装 (DeliverTopic 購読。方式は 2026-07-16 決定済み、購読許可・レイヤ利用の確認のみ)
5. ベンダー依頼: 地点詳細画面のリンクボタン (point-setup のボタン依頼と同時にまとめると効率的)

---

## 改訂履歴

| バージョン | 日付 | 改訂内容 |
|---|---|---|
| v0.1 | 2026-07-14 | 初版。販売動線 2 本の整理、SSO 契約 (ui-lte-m 同型・管理 API トークン不要)、画面設計 (設定 + 判定履歴、image-analysis 部品流用)、DB 設計 (settings / results / S3)、着信フック 3 案比較 (鍵論点)、将来構想 (IFRAME ウィジェット / LINE / ワークフロー版)、モックファースト開発計画を記録 |
| v0.2 | 2026-07-14 | spot_code 書式の誤りを訂正 (ユーザー指摘): 2 要素は LTE-M 機器限定の例外であり、NetA 配下機器の地点 CD は `通信機アカウント-NetAアドレス-機器型番` の 3 要素 (point-setup 構想メモ / redmine-cs #2744)。例を 3 要素 (`sc00000001-02-CAM-1`) に修正し、カメラの実書式確認を論点 2 に明記 |
| v0.4 | 2026-07-14 | 着信フックを案 A-0 (受信 S3 バケットの EventBridge 購読) に決定。mail-backend 受信実装の実確認・3 方式の詳細比較・コスト試算は CAMERA-MONITOR-HOOK-COMPARISON_フック方式比較.md (新規) に記録 |
| v0.3 | 2026-07-14 | カメラは NetA 配下にのみ存在し mail-backend は NetA 専用と確認 (ユーザー回答)。spot_code は常に 3 要素の地点 CD で確定し、論点 2 を機器型番の実例と画像メール→spot_code 対応付けに絞り込み |
| v0.5 | 2026-07-16 | 着信フックを案 A-3 (既存 DeliverTopic (SNS) の購読) に変更決定。A-0 は mail-backend 管理側の回答 (受信バケットの設定変更不可) により不成立。DeliverTopic はメール ID 入り永続キーと解析ライブラリが既存の拡張用トピックで mail-backend 変更ゼロ (比較資料 v1.1 参照)。論点 8 (購読の実装条件) を追加 |
