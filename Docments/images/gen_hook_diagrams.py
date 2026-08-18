# -*- coding: utf-8 -*-
"""camera-monitor 着信フック3案のアーキテクチャ図を生成する (redmine-dev #4658)"""
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.integration import Eventbridge, SimpleNotificationServiceSns
from diagrams.aws.engagement import SimpleEmailServiceSes
from diagrams.aws.network import APIGateway
from diagrams.aws.storage import S3
from diagrams.onprem.client import Users

BASE = "."

graph_attr = {
    "fontsize": "16",
    "fontname": "Noto Sans CJK JP",
    "bgcolor": "white",
    "pad": "0.3",
    "nodesep": "0.4",
    "ranksep": "0.7",
    "dpi": "200",
}
node_attr = {
    "fontsize": "10",
    "fontname": "Noto Sans CJK JP",
    "width": "1.1",
    "height": "1.3",
}
edge_attr = {
    "fontsize": "9",
    "fontname": "Noto Sans CJK JP",
    "color": "#666666",
}

HOOK = {"color": "#CC0000", "penwidth": "2.0"}
EXIST = {"bgcolor": "#F5F5F5", "style": "rounded"}
NEW = {"bgcolor": "#FFF4E5", "style": "rounded"}


def mail_front():
    camera = Users("観測カメラ\n(NetA/mail-svc)")
    ses_in = SimpleEmailServiceSes("SES 受信")
    inbox = S3("受信バケット\ninbox/{message_id}")
    camera >> Edge(label="メール添付画像") >> ses_in >> inbox
    return camera, ses_in, inbox


def mail_backend_core(subscriber_label="Subscriber\n(既存・無改修)"):
    sns = SimpleNotificationServiceSns("Receive Topic\n(SNS)")
    subscriber = Lambda(subscriber_label)
    deliver = Users("既存配信\n(連携元SaaS_A 連携\ntransfer-server 等)")
    sns >> subscriber >> Edge(label="従来どおり") >> deliver
    return sns, subscriber, deliver


def monitor_core():
    ingest = Lambda("ingest\n(画像メール判定\nspot_code 組立)")
    settings = Dynamodb("監視設定\nsettings")
    results = Dynamodb("判定履歴\nresults")
    images = S3("画像ストア\nlatest / results")
    api = APIGateway("image-analysis\n/workflow/compare")
    ses_out = SimpleEmailServiceSes("SES 通知")
    dest = Users("通知先\n(To/CC/BCC)")
    ingest >> Edge(label="設定照会", style="dashed") >> settings
    ingest >> Edge(label="AI 判定 (M2M)") >> api
    ingest >> results
    ingest >> images
    ingest >> Edge(label="危険時のみ", color="#CC0000") >> ses_out >> dest
    return ingest


def diagram(name, title):
    return Diagram(
        title,
        filename=f"{BASE}/{name}",
        outformat="png",
        direction="LR",
        show=False,
        graph_attr=graph_attr,
        node_attr=node_attr,
        edge_attr=edge_attr,
    )


# ---- 案 A-0: S3 EventBridge 購読 (mail-backend 無改修) ----
with diagram("hook-a0", "案 A-0: S3 EventBridge 購読 (不採用: バケット設定変更が不可)"):
    with Cluster("mail-backend (既存・無改修)", graph_attr=EXIST):
        camera, ses_in, inbox = mail_front()
        sns, subscriber, deliver = mail_backend_core()
        inbox >> sns
    with Cluster("camera-monitor (新規)", graph_attr=NEW):
        eb = Eventbridge("EventBridge\n(default bus)")
        ingest = monitor_core()
        eb >> Edge(label="inbox/ のみルール", **HOOK) >> ingest
    inbox >> Edge(label="EventBridge 通知有効化\n(バケット設定のみ)", **HOOK) >> eb

# ---- 案 A-1: Subscriber 改修でイベント発行 ----
with diagram("hook-a1", "案 A-1: Subscriber 改修でイベント発行 (画像メールのみ通知)"):
    with Cluster("mail-backend (既存・一部改修)", graph_attr=EXIST):
        camera, ses_in, inbox = mail_front()
        sns, subscriber, deliver = mail_backend_core(
            "Subscriber\n(改修: 画像メール判定\n+イベント発行 数行)")
        inbox >> sns
    with Cluster("camera-monitor (新規)", graph_attr=NEW):
        eb = Eventbridge("EventBridge\n(カスタムイベント)")
        ingest = monitor_core()
        eb >> ingest
    subscriber >> Edge(label="画像メール着信イベント\n{account, message_id, address}", **HOOK) >> eb

# ---- 案 A-2: NetaMailTable DynamoDB Streams ----
with diagram("hook-a2", "案 A-2: NetaMailTable の DynamoDB Streams 購読 (書込経路は要確認)"):
    with Cluster("mail-backend (既存・無改修)", graph_attr=EXIST):
        camera, ses_in, inbox = mail_front()
        sns, subscriber, deliver = mail_backend_core()
        inbox >> sns
        neta_mail = Dynamodb("NetaMailTable\n(JSON/Base64 変換済)")
        subscriber >> Edge(label="書込経路は要確認\n(Worker 等の可能性)",
                           style="dashed") >> neta_mail
    with Cluster("camera-monitor (新規)", graph_attr=NEW):
        ingest = monitor_core()
    neta_mail >> Edge(label="DynamoDB Streams\n(Streams 有効化が必要)", **HOOK) >> ingest

# ---- 案 A-3: DeliverTopic (SNS) 購読 (採用) ----
with diagram("hook-a3", "案 A-3: DeliverTopic (SNS) 購読 (mail-backend 変更ゼロ・採用案)"):
    with Cluster("mail-backend (既存・無改修)", graph_attr=EXIST):
        camera, ses_in, inbox = mail_front()
        sns, subscriber, deliver = mail_backend_core()
        inbox >> sns
        store = S3("リポジトリ保存\naccounts/{account}/\nmessages/{メールID}")
        deliver_topic = SimpleNotificationServiceSns("DeliverTopic\n(拡張用・既存)")
        subscriber >> Edge(label="アカウント別に保存") >> store
        subscriber >> Edge(label="配信の都度 publish\n(既存実装)") >> deliver_topic
    with Cluster("camera-monitor (新規)", graph_attr=NEW):
        ingest = monitor_core()
    deliver_topic >> Edge(label="SNS 購読を追加\n(フィルタ: Role=SUBSCRIBER)", **HOOK) >> ingest
    ingest >> Edge(label="対象メールのみ本体取得\n(Library)", style="dashed") >> store

print("generated: hook-a0.png / hook-a1.png / hook-a2.png / hook-a3.png")
