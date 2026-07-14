"""
logger.py

IRIS Trade Assistant の解析履歴モジュール。

役割:
    AIの予想（通貨ペア・方向・確信度・理由・読み取った価格など）を
    history.json に記録し、後から検索・集計できるようにする。

    各エントリには "outcome"（WIN / LOSS / PENDING / UNKNOWN）を持たせる。
    予想時点の価格が読み取れていれば、指定した時間が経過した後に
    実際の価格と比較して自動で正解・不正解を判定できる
    （resolve_outcome() を使う。monitor.py から呼ばれる想定）。
    価格が読み取れなかった場合は update_outcome() で手動更新もできる。

使い方:
    from logger import TradeLogger

    logger = TradeLogger()

    entry_id = logger.log(
        currency="USD/JPY",
        direction="HIGH",
        confidence=72,
        reason="上昇継続",
        price=151.234,
        horizon_seconds=20,
    )

    # 時間が経過した後、実際の価格が分かったら
    logger.resolve_outcome(entry_id, actual_price=151.4)

    history = logger.get_all(limit=50)
"""

import json
import uuid
from datetime import datetime
from pathlib import Path


VALID_OUTCOMES = ("PENDING", "WIN", "LOSS", "UNKNOWN")


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
        direction: str,
        confidence: int,
        reason: str = "",
        price: float = None,
        horizon_seconds: int = 20,
        image_path: str = None,
    ) -> str:
        """
        AIの予想を1件記録する。

        Returns:
            発行されたエントリID（文字列）。resolve_outcome() / update_outcome() で使う。
        """
        entry_id = uuid.uuid4().hex[:12]

        entry = {
            "id": entry_id,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "currency": currency,
            "direction": direction,
            "confidence": confidence,
            "reason": reason,
            "predicted_price": price,
            "actual_price": None,
            "horizon_seconds": horizon_seconds,
            "image_path": image_path,
            "outcome": "PENDING",
        }

        self.entries.append(entry)
        self._write()

        return entry_id

    def resolve_outcome(self, entry_id: str, actual_price: float) -> str:
        """
        horizon_seconds経過後の実際の価格を渡し、
        予想（HIGH/LOW）が当たっていたかを自動判定して記録する。

        Returns:
            判定結果（"WIN" / "LOSS" / "UNKNOWN"）。
            該当エントリが無い、または予想時点の価格が記録されていない場合は "UNKNOWN"。
        """
        entry = self.get_by_id(entry_id)

        if entry is None or entry.get("predicted_price") is None:
            return "UNKNOWN"

        predicted_price = entry["predicted_price"]

        if actual_price > predicted_price:
            actual_direction = "HIGH"
        elif actual_price < predicted_price:
            actual_direction = "LOW"
        else:
            actual_direction = None  # 価格が変化していない

        if actual_direction is None:
            outcome = "UNKNOWN"
        elif actual_direction == entry["direction"]:
            outcome = "WIN"
        else:
            outcome = "LOSS"

        entry["actual_price"] = actual_price
        entry["outcome"] = outcome
        self._write()

        return outcome

    def update_outcome(self, entry_id: str, outcome: str) -> bool:
        """
        指定したエントリの結果（WIN / LOSS / PENDING / UNKNOWN）を手動で更新する。

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

    def get_by_currency(self, currency: str, limit: int = None) -> list:
        """指定した通貨ペアの履歴のみ、新しい順に取得する。"""
        filtered = [e for e in reversed(self.entries) if e["currency"] == currency]

        if limit is not None:
            filtered = filtered[:limit]

        return filtered

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
        direction="HIGH",
        confidence=72,
        reason="動作確認用のテストエントリ",
        price=151.234,
        horizon_seconds=20,
    )

    print("記録したエントリID:", eid)
    print("判定結果:", logger.resolve_outcome(eid, actual_price=151.5))
    print("直近の履歴:", logger.get_all(limit=5))
