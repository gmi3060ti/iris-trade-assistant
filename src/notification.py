"""
notification.py

IRIS Trade Assistant の通知モジュール。

役割:
    BUY/SELLシグナル発生時に、LINEへ通知を送る。

    「LINE Notify」は2025年3月31日にサービス終了したため、
    LINEが公式に代替として案内している「LINE Messaging API」を使う。

    このIRIS専用の公式アカウントは基本的に自分しか
    友だち追加しない前提のため、「Broadcast（友だち全員へ配信）」を使う。
    ユーザーIDを調べる必要がなく、チャネルアクセストークンだけで送れる。

    無料枠（コミュニケーションプラン）は月200通まで。
    「送信先の友だち数 × メッセージ数」でカウントされるため、
    自分1人だけが友だちなら、実質「送った回数」がそのままカウント数になる。

事前準備（初回のみ）:
    1. LINE公式アカウントを作成する
       https://manager.line.biz/

    2. LINE Official Account Managerで「Messaging API」を有効化する
       （自動的にLINE DevelopersにMessaging APIチャネルが作られる）

    3. LINE Developersコンソールで、そのチャネルの
       「Messaging API設定」タブから「チャネルアクセストークン（長期）」を発行する
       https://developers.line.biz/

    4. 自分のLINEアカウントで、その公式アカウントを「友だち追加」する

    5. IRISのSettings画面で、チャネルアクセストークンを入力して保存する

使い方:
    from config import Config
    from notification import LineNotifier

    config = Config()
    notifier = LineNotifier(config)

    result = notifier.send("BUYシグナル発生（Confidence 85%）")

    if not result["success"]:
        print(result["error"])
"""

import json
import urllib.request
import urllib.error


LINE_BROADCAST_API_URL = "https://api.line.me/v2/bot/message/broadcast"

# LINEの1メッセージあたりの文字数上限（超過分は切り詰める）
_MAX_MESSAGE_LENGTH = 5000


class LineNotifier:
    """
    LINE Messaging API（Broadcast Message）で通知を送るクラス。

    Args:
        config: Config インスタンス。line_channel_access_token を参照する。
    """

    def __init__(self, config):
        self.config = config

    def send(self, message: str) -> dict:
        """
        LINEに友だち全員宛（実質は自分宛）でテキストメッセージを送信する。

        Returns:
            {"success": bool, "error": str または None}
        """
        token = self.config.get("line_channel_access_token", "")

        if not token:
            return {
                "success": False,
                "error": (
                    "LINEのチャネルアクセストークンが未設定です。"
                    "Settings画面から設定してください。"
                ),
            }

        payload = {
            "messages": [
                {
                    "type": "text",
                    "text": message[:_MAX_MESSAGE_LENGTH],
                }
            ],
        }

        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            LINE_BROADCAST_API_URL,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                if 200 <= response.status < 300:
                    return {"success": True, "error": None}

                return {
                    "success": False,
                    "error": f"LINE APIエラー（status={response.status}）",
                }

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            return {
                "success": False,
                "error": f"LINE APIエラー（{e.code}）: {body}",
            }

        except urllib.error.URLError as e:
            return {
                "success": False,
                "error": f"通信エラー: {e.reason}",
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"予期しないエラー: {e}",
            }

    @staticmethod
    def build_signal_message(currency: str, result: dict) -> str:
        """
        解析結果からLINE通知用のメッセージ文を組み立てる。

        Args:
            currency: 通貨ペア（例: "USD/JPY"）
            result: analyzer.analyze() や scoring の結果を含む辞書。
                trend / confidence / recommendation / reason を使う。
                stop_loss_percent / take_profit_percent があれば追記する。
        """
        lines = [
            "【IRIS Trade Assistant】",
            f"通貨: {currency}",
            f"判断: {result.get('recommendation', '-')}",
            f"トレンド: {result.get('trend', '-')}",
            f"確信度: {result.get('confidence', 0)}%",
        ]

        if result.get("reason"):
            lines.append(f"理由: {result['reason']}")

        if "stop_loss_percent" in result and "take_profit_percent" in result:
            lines.append(
                f"目安 損切り: -{result['stop_loss_percent']}% "
                f"/ 利確: +{result['take_profit_percent']}%"
            )

        return "\n".join(lines)


if __name__ == "__main__":
    # 簡易動作確認（実際に送るには config.json に
    # line_channel_access_token が必要）
    from config import Config

    cfg = Config()
    notifier = LineNotifier(cfg)

    test_result = {
        "trend": "UP",
        "confidence": 85,
        "recommendation": "BUY",
        "reason": "テスト通知です",
    }

    message = LineNotifier.build_signal_message("USD/JPY", test_result)
    print(notifier.send(message))
