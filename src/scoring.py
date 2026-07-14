"""
scoring.py

IRIS Trade Assistant の資金管理・成績集計モジュール。

役割:
    1. Settingsの口座残高・リスク許容率から、
       1回のHigh/Low予想あたりの「推奨ベット額」を計算する。
    2. logger.py に記録された履歴から勝率を集計する。

注意（重要）:
    ここでの「推奨ベット額」は、単純に
    「口座残高 × リスク許容率」で計算しているだけの目安であり、
    投資助言ではありません。実際の資金管理は自分の判断で行ってください。

使い方:
    from config import Config
    from scoring import RiskCalculator

    config = Config()
    risk = RiskCalculator(config)

    bet = risk.calculate_max_loss()
    print(bet)
    # {"account_balance": 100000, "risk_percent": 2.0, "max_loss_amount": 2000.0}

    from logger import TradeLogger
    logger = TradeLogger()
    stats = risk.calculate_win_rate(logger.get_all())
    print(stats)
"""


class RiskCalculator:
    """
    資金管理・成績集計を行うクラス。

    Args:
        config: Config インスタンス。account_balance / risk_percent を参照する。
    """

    def __init__(self, config):
        self.config = config

    # ==========================
    # 推奨ベット額
    # ==========================

    def calculate_max_loss(self) -> dict:
        """
        Settingsの口座残高とリスク許容率から、
        1回の予想あたりの推奨ベット額（＝許容できる最大損失額）を計算する。
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

    @staticmethod
    def calculate_win_rate_by_currency(history: list) -> dict:
        """
        通貨ペアごとの勝率を集計する。

        Returns:
            {"USD/JPY": {...calculate_win_rateと同じ形式...}, ...}
        """
        by_currency = {}

        for entry in history:
            currency = entry.get("currency", "-")
            by_currency.setdefault(currency, []).append(entry)

        return {
            currency: RiskCalculator.calculate_win_rate(entries)
            for currency, entries in by_currency.items()
        }


if __name__ == "__main__":
    # 簡易動作確認
    from config import Config

    cfg = Config()
    risk = RiskCalculator(cfg)

    print(risk.calculate_max_loss())

    sample_history = [
        {"currency": "USD/JPY", "outcome": "WIN"},
        {"currency": "USD/JPY", "outcome": "WIN"},
        {"currency": "USD/JPY", "outcome": "LOSS"},
        {"currency": "EUR/USD", "outcome": "LOSS"},
        {"currency": "EUR/USD", "outcome": "PENDING"},
    ]
    print(RiskCalculator.calculate_win_rate(sample_history))
    print(RiskCalculator.calculate_win_rate_by_currency(sample_history))
