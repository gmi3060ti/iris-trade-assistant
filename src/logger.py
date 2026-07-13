"""
logger.py

IRIS Trade Assistant の解析履歴モジュール。

役割:
    AI解析の結果（トレンド・確信度・売買判断・理由など）を
    history.json に記録し、後から検索・集計できるようにする。

    各エントリには "outcome"（WIN / LOSS / PENDING）を持たせられる。
    IRIS自体は将来の価格を知らないため、勝敗の自動判定はできない。
    outcomeは既定で "PENDING" になり、必要に応じて
    update_outcome() で後から手動更新する想定。
    （scoring.py の勝率計算は、この outcome を使って行う）

使い方:
    from logger import TradeLogger

    logger = TradeLogger()

    entry_id = logger.log(
        currency="USD/JPY",
        trend="UP",
        confidence=82,
        recommendation="BUY",
        reason="上昇トレンド継続",
        stop_loss_percent=1.0,
        take_profit_percent=2.0,
    )

    logger.update_outcome(entry_id, "WIN")

    history = logger.get_all(limit=50)
"""

import json
import uuid
from datetime import datetime
from pathlib import Path


VALID_OUTCOMES = ("PENDING", "WIN", "LOSS")


class TradeLogger:
    """
    解析結果の履歴を管理するクラス。

    Args:
        path: 履歴を保存するJSONファイルのパス（デフォルト: "history.json"）
    """

    def __init__(self, path: str = "history.json"):
        self.path = Path(path)
        self.entries = self._load()

    # ==========================
    # 内部処理
    # ==========================

    def _load(self) -> list:
        """history.json を読み込む。存在しない・壊れている場合は空リストから開始する。"""
        if not self.path.exists():
            return []

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        if not isinstance(data, list):
            return []

        return data

    def _write(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, ensure_ascii=False, indent=2)

    # ==========================
    # 公開メソッド
    # ==========================

    def log(
        self,
        currency: str,
        trend: str,
        confidence: int,
        recommendation: str,
        reason: str = "",
        image_path: str = None,
        entry_price: float = None,
        stop_loss_percent: float = None,
        take_profit_percent: float = None,
    ) -> str:
        """
        解析結果を1件記録する。

        Returns:
            発行されたエントリID（文字列）。update_outcome() で使う。
        """
        entry_id = uuid.uuid4().hex[:12]

        entry = {
            "id": entry_id,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "currency": currency,
            "trend": trend,
            "confidence": confidence,
            "recommendation": recommendation,
            "reason": reason,
            "image_path": image_path,
            "entry_price": entry_price,
            "stop_loss_percent": stop_loss_percent,
            "take_profit_percent": take_profit_percent,
            "outcome": "PENDING",
        }

        self.entries.append(entry)
        self._write()

        return entry_id

    def update_outcome(self, entry_id: str, outcome: str) -> bool:
        """
        指定したエントリの結果（WIN / LOSS / PENDING）を更新する。

        Returns:
            更新できた場合 True、該当エントリが無い場合 False。
        """
        if outcome not in VALID_OUTCOMES:
            raise ValueError(
                f"outcome は {VALID_OUTCOMES} のいずれかである必要があります: {outcome}"
            )

        for entry in self.entries:
            if entry["id"] == entry_id:
                entry["outcome"] = outcome
                self._write()
                return True

        return False

    def get_all(self, limit: int = None) -> list:
        """
        履歴を新しい順に取得する。

        Args:
            limit: 取得件数の上限（Noneなら全件）
        """
        ordered = list(reversed(self.entries))

        if limit is not None:
            ordered = ordered[:limit]

        return ordered

    def get_by_id(self, entry_id: str):
        """IDを指定して1件取得する。見つからなければ None。"""
        for entry in self.entries:
            if entry["id"] == entry_id:
                return entry
        return None

    def get_pending(self) -> list:
        """outcomeがまだ判定されていない（PENDING）エントリのみ取得する。"""
        return [e for e in self.entries if e["outcome"] == "PENDING"]


if __name__ == "__main__":
    # 簡易動作確認
    logger = TradeLogger()

    eid = logger.log(
        currency="USD/JPY",
        trend="UP",
        confidence=82,
        recommendation="BUY",
        reason="動作確認用のテストエントリ",
    )

    print("記録したエントリID:", eid)
    print("直近の履歴:", logger.get_all(limit=5))
