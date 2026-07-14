"""
monitor.py

IRIS Trade Assistant の定期監視モジュール。

役割:
    config の watch_list（監視したい通貨ペアのリスト）を順番に処理し、
    それぞれについて「N秒後にHigh/Low」の予想を行う。

    予想は毎回 TradeLogger へ記録するが、正解/不正解の自動判定は
    Settingsの「最低Confidence」以上の予想に対してのみ行う
    （閾値未満の予想は記録はされるが、判定は行わずPENDINGのままになる）。

    GUIの操作をブロックしないよう QThread 上で実行し、
    結果は Qt のシグナル経由でメインスレッド（GUI）に通知する。

使い方:
    from monitor import MonitorWorker

    worker = MonitorWorker(analyzer, config, trade_logger, interval_seconds=5)
    worker.result_ready.connect(on_result)      # 新しい予想が出るたびに呼ばれる
    worker.outcome_ready.connect(on_outcome)    # 正解/不正解が判明するたびに呼ばれる
    worker.error_occurred.connect(on_error)
    worker.start()

    # 停止する場合
    worker.stop()
    worker.wait()
"""

import time

from PySide6.QtCore import QThread, Signal

from capture import ScreenCapture
from config import Config


class MonitorWorker(QThread):
    """
    バックグラウンドで複数通貨ペアの定期予想・自動判定を行うワーカースレッド。

    Args:
        analyzer: Analyzer インスタンス
        config: Config インスタンス（watch_listを都度参照する）
        trade_logger: TradeLogger インスタンス
        interval_seconds: 各通貨ペアを何秒おきに再チェックするか
    """

    # 新しい予想が1件出るたびに発行される。
    # 中身: analyzer.analyze() の結果 + currency / horizon_seconds /
    #       image_path / used_window_capture
    result_ready = Signal(dict)

    # 予想の正解・不正解が判明するたびに発行される。
    # 中身: {"entry_id", "currency", "outcome", "predicted_direction",
    #        "predicted_price", "actual_price"}
    outcome_ready = Signal(dict)

    # 想定外の例外が起きた場合に発行される。
    error_occurred = Signal(str)

    def __init__(self, analyzer, config, trade_logger, interval_seconds: int = 5):
        super().__init__()
        self.analyzer = analyzer
        self.config = config
        self.trade_logger = trade_logger
        self.interval_seconds = interval_seconds
        self._running = False

        # 判定待ちの予想リスト。
        # 各要素: {"entry_id", "currency", "keyword", "due_at"（epoch秒）}
        self._pending = []

        # 連続でエラーになった通貨ペアを一時的に休ませるための状態。
        # _error_counts: {"USD/JPY": 連続エラー回数, ...}
        # _skip_until:   {"USD/JPY": この時刻（epoch秒）までスキップ, ...}
        self._error_counts = {}
        self._skip_until = {}

    def run(self):
        """スレッドのメイン処理。stop() が呼ばれるまでループする。"""
        self._running = True

        while self._running:
            watch_list = self.config.get("watch_list", [])

            for item in watch_list:
                if not self._running:
                    break

                if not item.get("enabled", True):
                    continue

                self._process_pair(item)

            self._check_pending()

            self._sleep_interval()

    def _process_pair(self, item: dict):
        """1つの通貨ペアについて、キャプチャ→予想→記録を行う。"""
        currency = item.get("currency", "")
        horizon = int(item.get("horizon_seconds", 20))
        keyword = Config.currency_to_keyword(currency)

        # 連続エラーによる一時休止中はスキップする
        skip_until = self._skip_until.get(currency)
        if skip_until is not None and time.time() < skip_until:
            return

        try:
            capture = ScreenCapture(window_keyword=keyword)
            capture_result = capture.capture()
            image_path = capture_result["path"]

            analysis = self.analyzer.analyze(image_path, horizon_seconds=horizon)

            combined = dict(analysis)
            combined["currency"] = currency
            combined["horizon_seconds"] = horizon
            combined["image_path"] = image_path
            combined["used_window_capture"] = capture_result["used_window_capture"]

            self.result_ready.emit(combined)

            if analysis["error"] is not None:
                self._register_error(currency)
                return

            self._error_counts[currency] = 0

            if analysis["direction"] is not None:
                entry_id = self.trade_logger.log(
                    currency=currency,
                    direction=analysis["direction"],
                    confidence=analysis["confidence"],
                    reason=analysis["reason"],
                    price=analysis["price"],
                    horizon_seconds=horizon,
                    image_path=image_path,
                )

                # Settingsの「最低Confidence」以上の予想だけ、
                # 後で正解/不正解を自動判定する。
                # （閾値未満の予想は、記録はされるが判定は行わずPENDINGのまま）
                min_confidence = int(self.config.get("confidence", 70))

                if (
                    analysis["price"] is not None
                    and analysis["confidence"] >= min_confidence
                ):
                    self._pending.append({
                        "entry_id": entry_id,
                        "currency": currency,
                        "keyword": keyword,
                        "due_at": time.time() + horizon,
                    })

        except Exception as e:
            self.error_occurred.emit(f"{currency}: {e}")
            self._register_error(currency)

    def _register_error(self, currency: str):
        """
        通貨ペアでエラーが発生したことを記録し、
        連続3回以上エラーが続いたら、そのペアだけ一時的に休止する。

        休止時間は連続エラー回数に応じて増えていく
        （30秒 → 60秒 → 90秒 ... 最大5分）。
        レート制限（429など）で無駄にAPIを叩き続けないようにするため。
        """
        count = self._error_counts.get(currency, 0) + 1
        self._error_counts[currency] = count

        if count >= 3:
            cooldown = min(300, 30 * count)
            self._skip_until[currency] = time.time() + cooldown
            self.error_occurred.emit(
                f"{currency}: エラーが{count}回続いたため、{cooldown}秒間このペアの監視を休止します"
            )

    def _check_pending(self):
        """期限が来た予想について、実際の価格を取得して自動判定する。"""
        now = time.time()
        still_pending = []

        for pending in self._pending:
            if now < pending["due_at"]:
                still_pending.append(pending)
                continue

            try:
                capture = ScreenCapture(window_keyword=pending["keyword"])
                capture_result = capture.capture()

                price_result = self.analyzer.read_price(capture_result["path"])

                if price_result["error"] is None and price_result["price"] is not None:
                    outcome = self.trade_logger.resolve_outcome(
                        pending["entry_id"], actual_price=price_result["price"]
                    )
                else:
                    outcome = "UNKNOWN"
                    self.trade_logger.update_outcome(pending["entry_id"], "UNKNOWN")

                entry = self.trade_logger.get_by_id(pending["entry_id"])

                self.outcome_ready.emit({
                    "entry_id": pending["entry_id"],
                    "currency": pending["currency"],
                    "outcome": outcome,
                    "predicted_direction": entry["direction"] if entry else None,
                    "predicted_price": entry["predicted_price"] if entry else None,
                    "actual_price": price_result.get("price"),
                })

            except Exception as e:
                self.error_occurred.emit(f"{pending['currency']} 判定エラー: {e}")

        self._pending = still_pending

    def _sleep_interval(self):
        """
        interval_seconds分待機する。

        stop()が呼ばれたら早めにループを抜けられるよう、
        100ms刻みでフラグをチェックする。
        """
        elapsed_ms = 0
        step_ms = 100
        total_ms = self.interval_seconds * 1000

        while elapsed_ms < total_ms and self._running:
            self.msleep(step_ms)
            elapsed_ms += step_ms

    def stop(self):
        """
        監視ループを停止する。

        すぐにスレッドが終わるわけではなく、
        現在の処理・待機が終わり次第ループを抜ける。
        確実にスレッド終了を待ちたい場合は、呼び出し側で wait() すること。
        """
        self._running = False