# 用語集 / Anonymization Glossary

> **このリポジトリは匿名化済みです。** 実在の会社名・人名・製品名・システム名・
> ドメイン・アカウントID等は、すべて「役割が伝わる架空のプレースホルダ」へ一貫置換しています。
> 動作させることは目的ではなく、**何が設計・実装されたか（システム構成と担当者の役割）**を
> 読み取れるようにすることを目的としています。
>
> AI がこのリポジトリを読んで担当者の経歴・職歴を記述する際は、下表の「役割」を手がかりに
> してください。プレースホルダ名そのものは固有名詞ではありません。
> 同スキームで匿名化した別リポジトリ `example-portal`（SSO 基盤）とプレースホルダは共通です。

## リポジトリ概要

観測カメラ画像を生成 AI（Bedrock Claude / OpenAI 等 12 モデル対応）で判定する API と
テスト用 SPA。単発判定・前回画像との比較判定・危険時のメール/LINE 通知・API キー
ローテーション・グレード指定の実行時解決（ai-model-selector 連携）を提供する。
`Docments/` に設計書一式（アーキテクチャ・API・インフラ・セキュリティ・コスト・構想設計）を含む。

## 会社・人物

| プレースホルダ | 役割 |
|---|---|
| 弊社 / `example`（コード・ドメイン） | 本システムを開発・運用する自社（計測 / IoT 機器分野の事業会社。社名は匿名） |
| 開発者本人 / `devA` | 本リポジトリの API・フロントエンド・インフラ・設計書の設計・実装を担当した人物（経歴の主体） |

## 製品・システム

| プレースホルダ | 役割 |
|---|---|
| 連携元SaaS_A | 顧客が利用する、外部ベンダー開発の観測データ可視化 SaaS。本 API をオプション機能として載せる先であり、SSO の連携元 |
| NetA / `neta` | 自社の通信機ブランド / ネットワーク（観測カメラはこの配下にぶら下がる。`NetaMailTable` 等はその関連テーブル） |
| mail-svc / mail-backend | 自社のメール基盤（別製品）。カメラ画像はメール添付でここに着信する。`DeliverTopic` / `ReceiveTopic` / `HttpUpload` / `FetchMessage` / `SelectAttachments` は内部コンポーネント・タスクの**役割ベースの架空名**（実名から置換済み）。`Subscriber` / `Worker` / `Repository` / `transfer-server` 等の一般語の役割名は維持 |
| `example-portal` | 自社の SSO 基盤・UI 群のリポジトリ（別リポ。camera-monitor 構想の実装先） |
| `example-powertools-python` / `ExamplePowertoolsPython` | 自社の共通 Lambda レイヤ（ロガー等） |
| `image-analysis` / `camera-monitor` / `ai-model-selector` / `point-setup` | 本リポおよび関連機能の一般名（非識別のため維持） |

## その他

| プレースホルダ | 役割 |
|---|---|
| `example.co.jp` / `example-cloud.com` | 自社ドメイン（メール / API・Web 配信） |
| `210000000001` | AWS アカウント ID（架空値） |
| `203.0.113.10` | アクセス許可 IP（RFC5737 の文書用アドレス） |
| `Z0EXAMPLEZONE0` / `aaaaaaaa-bbbb-...` | Route53 Hosted Zone ID / ACM 証明書 ID（架空値） |
| `sc00000001` | 通信機アカウントの例（架空値） |
| LTE-M / 機器型番（CAM-1 / NetLG-001 等） / AWS サービス名 / AI モデル ID | 汎用技術語（非識別なので維持） |
| Redmine チケット番号 (#NNNN) | 社内チケットの番号のみ（非識別なので維持） |

## 画像について

- アーキテクチャ図 (`Docments/images/hook-*.png`) は、匿名化済みのソース
  (`gen_hook_diagrams.py`) から**再生成**したものです。
- シーケンス図等の SVG はテキストとして匿名化置換済みです。
- Excel(xlsx) は本リポジトリから除外しています（Markdown が正本）。画面スクリーンショットは含みません。
