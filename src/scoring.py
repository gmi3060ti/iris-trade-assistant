"""
scoring.py

IRIS Trade Assistant のリスク管理・成績集計モジュール。

役割:
    1. AIの判断（BUY/SELL, Confidence）から、
       損切り・利確の目安（%ベース）と最大損失額を計算する。
    2. logger.py に記録された履歴から勝率を集計する。

注意（重要）:
    ここで計算する損切り・利確ラインは、実際の価格データに基づいた
    予測ではなく、Confidenceに応じて損切りを狭め・利確を広げる
    という単純なヒューリスティック（経験則）です。
    投資助言ではありません。実際のトレードでは、自分の資金管理
    ルールやチャート状況と照らし合わせて判断してください。

使い方:
    from config import Config
    from scoring import RiskCalculator

    config = Config()
    risk = RiskCalculator(config)

    levels = risk.suggest_risk_levels(recommendation="BUY", confidence=82)
    print(levels)
    # {"stop_loss_percent": 0.8, "take_profit_percent": 2.4, "risk_reward_ratio": 3.0}

    loss = risk.calculate_max_loss()
    print(loss)
    # {"account_balance": 100000, "risk_percent": 2.0, "max_loss_amount": 2000.0}

    from logger import TradeLogger
    logger = TradeLogger()
    stats = risk.calculate_win_rate(logger.get_all())
    print(stats)
"""


class RiskCalculator:
    """
    リスク管理・成績集計を行うクラス。

    Args:
        config: Config インスタンス。
            account_balance / risk_percent /
            stop_loss_percent / take_profit_percent を参照する。
    """

    def __init__(self, config):
        self.config = config

    # ==========================
    # 損切り・利確の目安
    # ==========================

    def suggest_risk_levels(self, recommendation: str, confidence: int) -> dict:
        """
        BUY/SELLの判断とConfidenceから、損切り・利確の目安（%）を計算する。

        WAITの場合は損切り・利確の概念が無いため、すべて0を返す。

        考え方（単純なヒューリスティック）:
            - Settingsの stop_loss_percent / take_profit_percent を基準値とする
            - Confidenceが高いほど、損切り幅をやや狭く、利確幅をやや広くする
              （確信度が高い判断ほどリスクリワードを良くする、という単純な調整）
        """
        base_stop = float(self.config.get("stop_loss_percent", 1.0))
        base_take = float(self.config.get("take_profit_percent", 2.0))

        if recommendation not in ("BUY", "SELL"):
            return {
                "stop_loss_percent": 0.0,
                "take_profit_percent": 0.0,
                "risk_reward_ratio": 0.0,
            }

        # confidence 50を基準に、±50の範囲で最大±30%程度、基準値を調整する
        adjustment = max(-30, min(30, (confidence - 50))) / 100

        stop_loss_percent = round(base_stop * (1 - adjustment), 2)
        take_profit_percent = round(base_take * (1 + adjustment), 2)

        # 損切り幅が小さすぎ／マイナスにならないよう下限を設ける
        stop_loss_percent = max(stop_loss_percent, 0.1)

        risk_reward_ratio = round(take_profit_percent / stop_loss_percent, 2)

        return {
            "stop_loss_percent": stop_loss_percent,
            "take_profit_percent": take_profit_percent,
            "risk_reward_ratio": risk_reward_ratio,
        }

    # ==========================
    # 最大損失額
    # ==========================

    def calculate_max_loss(self) -> dict:
        """
        Settingsの口座残高とリスク許容率から、1トレードあたりの最大損失額を計算する。
        """
        account_balance = float(self.config.get("account_balance", 100000))
        risk_percent = float(self.config.get("risk_percent", 2.0))

        max_loss_amount = round(account_balance * (risk_percent / 100), 2)

        return {
            "account_balance": account_balance,
            "risk_percent": risk_percent,
            "max_loss_amount": max_loss_amount,
        }

    # ==========================
    # 勝率集計
    # ==========================

    @staticmethod
    def calculate_win_rate(history: list) -> dict:
        """
        logger.get_all() で取得した履歴から勝率を集計する。

        outcomeが "PENDING" のエントリは集計対象から除外する
        （まだ結果が確定していないため）。

        Returns:
            {
                "total": 全エントリ数,
                "decided": WIN/LOSSが確定しているエントリ数,
                "pending": PENDINGのエントリ数,
                "wins": WIN数,
                "losses": LOSS数,
                "win_rate": 勝率（%、decidedが0件なら None）,
            }
        """
        total = len(history)
        wins = sum(1 for e in history if e.get("outcome") == "WIN")
        losses = sum(1 for e in history if e.get("outcome") == "LOSS")
        pending = sum(1 for e in history if e.get("outcome") == "PENDING")

        decided = wins + losses
        win_rate = round(wins / decided * 100, 1) if decided > 0 else None

        return {
            "total": total,
            "decided": decided,
            "pending": pending,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
        }


if __name__ == "__main__":
    # 簡易動作確認
    from config import Config

    cfg = Config()
    risk = RiskCalculator(cfg)

    print(risk.suggest_risk_levels("BUY", 85))
    print(risk.suggest_risk_levels("SELL", 55))
    print(risk.suggest_risk_levels("WAIT", 50))
    print(risk.calculate_max_loss())

    sample_history = [
        {"outcome": "WIN"},
        {"outcome": "WIN"},
        {"outcome": "LOSS"},
        {"outcome": "PENDING"},
    ]
    print(RiskCalculator.calculate_win_rate(sample_history))
