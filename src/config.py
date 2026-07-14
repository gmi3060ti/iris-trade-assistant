"""
config.py

IRIS Trade Assistant の設定管理モジュール。

役割:
    設定内容（APIキー、監視する通貨ペアのリスト、AIモデル、Confidence、テーマ）を
    config.json に保存・読み込みする。

使い方:
    from config import Config

    config = Config()

    # 読み込み
    watch_list = config.get("watch_list")

    # 更新して保存
    config.set("watch_list", [
        {"currency": "USD/JPY", "horizon_seconds": 20, "enabled": True},
        {"currency": "EUR/USD", "horizon_seconds": 30, "enabled": True},
    ])
    config.save()

    # まとめて更新して保存
    config.update({
        "ai_model": "gemini-3.1-flash-lite",
        "confidence": 80,
    })
"""

import json
from pathlib import Path


class Config:
    """
    IRIS の設定を管理するクラス。

    設定は config.json に保存される。
    ファイルが存在しない場合や壊れている場合は、
    デフォルト値を使って新規作成する。
    """

    # デフォルト設定
    DEFAULTS = {
        "api_key": "",
        "ai_model": "gemini-3.1-flash-lite",
        "confidence": 70,
        "theme": "dark",
        # 監視する通貨ペアのリスト。
        # 各要素: {"currency": "USD/JPY", "horizon_seconds": 20, "enabled": True}
        # currencyからスペース・スラッシュを除いた文字列が、
        # 対応するTradingViewウィンドウを見分けるキーワードとして使われる
        # （例: "USD/JPY" -> "USDJPY"）。
        "watch_list": [
            {"currency": "USD/JPY", "horizon_seconds": 20, "enabled": True},
        ],
        # LINE通知（Messaging API）
        "line_channel_access_token": "",
        "notify_on_prediction": True,
        "monitor_interval_seconds": 5,
        # リスク管理
        "account_balance": 100000,
        "risk_percent": 2.0,
    }

    def __init__(self, path: str = "config.json"):
        self.path = Path(path)
        self.data = self._load()

    # ==========================
    # 内部処理
    # ==========================

    def _load(self) -> dict:
        """
        config.json を読み込む。

        存在しない場合、または壊れている場合は
        デフォルト値で新規作成して保存する。
        """
        if not self.path.exists():
            data = self.DEFAULTS.copy()
            self._write(data)
            return data

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            # 壊れたJSONの場合はデフォルトへリセット
            data = self.DEFAULTS.copy()
            self._write(data)
            return data

        # 欠けているキーがあればデフォルト値で補完する
        # （バージョンアップで設定項目が増えた場合に対応するため）
        updated = False
        for key, value in self.DEFAULTS.items():
            if key not in data:
                data[key] = value
                updated = True

        # 旧バージョン（単一のcurrency設定）からの移行
        if "currency" in data and "watch_list" in data:
            old_currency = data.pop("currency")
            # watch_listがまだデフォルトのまま（＝実質未設定）なら、
            # 旧設定の通貨ペアを引き継ぐ
            if data["watch_list"] == self.DEFAULTS["watch_list"]:
                data["watch_list"] = [
                    {
                        "currency": old_currency,
                        "horizon_seconds": 20,
                        "enabled": True,
                    }
                ]
            updated = True

        if updated:
            self._write(data)

        return data

    def _write(self, data: dict) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ==========================
    # 公開メソッド
    # ==========================

    def get(self, key: str, default=None):
        """設定値を1つ取得する。"""
        return self.data.get(key, default)

    def set(self, key: str, value) -> None:
        """設定値を1つ更新する（保存はされない。save()を呼ぶこと）。"""
        self.data[key] = value

    def update(self, values: dict) -> None:
        """複数の設定値をまとめて更新する（保存はされない）。"""
        self.data.update(values)

    def save(self) -> None:
        """現在の設定内容を config.json に保存する。"""
        self._write(self.data)

    def reset(self) -> None:
        """設定をデフォルト値にリセットして保存する。"""
        self.data = self.DEFAULTS.copy()
        self.save()

    def all(self) -> dict:
        """設定内容をすべて取得する（辞書のコピーを返す）。"""
        return self.data.copy()

    @staticmethod
    def currency_to_keyword(currency: str) -> str:
        """
        通貨ペア表記からウィンドウ検出用キーワードを作る。

        例: "USD/JPY" -> "USDJPY"

        TradingViewのウィンドウタイトルには通常
        スラッシュ無しのティッカー表記（USDJPYなど）が含まれるため、
        この形式に変換して検出に使う。
        """
        return currency.replace("/", "").replace(" ", "").upper()


if __name__ == "__main__":
    # 簡易動作確認
    config = Config()
    print("現在の設定:")
    print(json.dumps(config.all(), ensure_ascii=False, indent=2))
