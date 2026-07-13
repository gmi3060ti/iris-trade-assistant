"""
config.py

IRIS Trade Assistant の設定管理モジュール。

役割:
    設定内容（APIキー、通貨ペア、AIモデル、Confidence、テーマ）を
    config.json に保存・読み込みする。

使い方:
    from config import Config

    config = Config()

    # 読み込み
    currency = config.get("currency")

    # 更新して保存
    config.set("currency", "USD/JPY")
    config.save()

    # まとめて更新して保存
    config.update({
        "currency": "USD/JPY",
        "ai_model": "gemini-3.5-flash",
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
        "currency": "EUR/USD",
        "ai_model": "gemini-3.5-flash",
        "confidence": 70,
        "theme": "dark",
        # LINE通知（Messaging API）
        "line_channel_access_token": "",
        "notify_on_buy_sell": True,
        # リスク管理
        "account_balance": 100000,
        "risk_percent": 2.0,
        "stop_loss_percent": 1.0,
        "take_profit_percent": 2.0,
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


if __name__ == "__main__":
    # 簡易動作確認
    config = Config()
    print("現在の設定:")
    print(json.dumps(config.all(), ensure_ascii=False, indent=2))
