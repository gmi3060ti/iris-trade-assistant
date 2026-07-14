from capture import ScreenCapture
from datetime import datetime

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
)

from settings import SettingsDialog
from config import Config
from analyzer import Analyzer
from monitor import MonitorWorker
from logger import TradeLogger
from notification import LineNotifier
from scoring import RiskCalculator


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.config = Config()
        self.analyzer = Analyzer(self.config)
        self.monitor_worker = None
        self.trade_logger = TradeLogger()
        self.notifier = LineNotifier(self.config)
        self.risk = RiskCalculator(self.config)
        self._last_notified_direction = {}  # {"USD/JPY": "HIGH", ...}

        self.setWindowTitle("IRIS Trade Assistant β1")
        self.resize(860, 880)

        main_layout = QVBoxLayout()

        # ==========================
        # タイトル
        # ==========================

        title = QLabel("IRIS Trade Assistant")
        title.setStyleSheet(
            "font-size:24px;font-weight:bold;"
        )

        self.status = QLabel("🔴 OFFLINE")
        self.status.setStyleSheet(
            "font-size:16px;color:red;"
        )

        top = QHBoxLayout()
        top.addWidget(title)
        top.addStretch()
        top.addWidget(self.status)

        main_layout.addLayout(top)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)

        main_layout.addWidget(line)

        # ==========================
        # 情報
        # ==========================

        self.time_label = QLabel()

        self.winrate = QLabel(
            "勝率 : - (0勝0敗 / 判定待ち0件)"
        )

        for widget in (self.time_label, self.winrate):
            widget.setStyleSheet("font-size:15px;")
            main_layout.addWidget(widget)

        main_layout.addSpacing(10)

        # ==========================
        # チャート（直近にキャプチャした通貨ペアを表示）
        # ==========================

        chart_box = QGroupBox("📈 Chart（直近のキャプチャ）")

        chart_layout = QVBoxLayout()

        self.chart_label = QLabel(
            "キャプチャ画像がここに表示されます"
        )

        self.chart_label.setAlignment(
            Qt.AlignCenter
        )

        self.chart_label.setMinimumHeight(240)

        self.chart_label.setStyleSheet("""
            border:1px solid gray;
            border-radius:8px;
            background:#2b2b2b;
        """)

        chart_layout.addWidget(self.chart_label)

        chart_box.setLayout(chart_layout)

        main_layout.addWidget(chart_box)

        # ==========================
        # 通貨ペアごとの予想一覧
        # ==========================

        predictions_box = QGroupBox("🤖 AI Predictions")

        predictions_layout = QVBoxLayout()

        self.predictions_table = QTableWidget(0, 6)
        self.predictions_table.setHorizontalHeaderLabels([
            "通貨ペア", "予想", "確信度", "理由", "判定", "更新時刻",
        ])
        self.predictions_table.horizontalHeader().setStretchLastSection(True)
        self.predictions_table.setMinimumHeight(180)

        predictions_layout.addWidget(self.predictions_table)

        predictions_box.setLayout(predictions_layout)

        main_layout.addWidget(predictions_box)

        main_layout.addSpacing(10)

        # ==========================
        # ボタン
        # ==========================

        self.start_btn = QPushButton("▶ Start Monitor")
        self.stop_btn = QPushButton("■ Stop")
        self.capture_btn = QPushButton("📸 Capture（先頭の有効な通貨ペアのみ）")
        self.setting_btn = QPushButton("⚙ Settings")

        for button in (
            self.start_btn,
            self.stop_btn,
            self.capture_btn,
            self.setting_btn,
        ):
            button.setMinimumHeight(42)
            main_layout.addWidget(button)

        self.stop_btn.setEnabled(False)

        # ==========================
        # ログ
        # ==========================

        log_title = QLabel("ログ")
        log_title.setStyleSheet(
            "font-size:16px;font-weight:bold;"
        )

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        main_layout.addWidget(log_title)
        main_layout.addWidget(self.log)

        self.setLayout(main_layout)

        # ==========================
        # Signal
        # ==========================

        self.start_btn.clicked.connect(
            self.start_monitor
        )

        self.stop_btn.clicked.connect(
            self.stop_monitor
        )

        self.capture_btn.clicked.connect(
            self.capture_screen
        )

        self.setting_btn.clicked.connect(
            self.open_settings
        )

        # ==========================
        # Timer
        # ==========================

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.update_time
        )

        self.timer.start(1000)

        self.update_time()
        self._update_winrate_label()

        self.add_log("IRIS 起動")
        self.add_log("待機中...")

    def update_time(self):
        now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        self.time_label.setText(f"現在時刻 : {now}")

    def add_log(self, message):
        now = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{now}] {message}")

    # ==========================
    # 監視の開始・停止
    # ==========================

    def start_monitor(self):
        if self.monitor_worker is not None:
            return  # すでに監視中

        watch_list = self.config.get("watch_list", [])
        enabled_pairs = [w for w in watch_list if w.get("enabled", True)]

        if not enabled_pairs:
            self.add_log("監視する通貨ペアが設定されていません（Settingsで追加してください）")
            return

        interval = int(self.config.get("monitor_interval_seconds", 5))

        self.monitor_worker = MonitorWorker(
            self.analyzer, self.config, self.trade_logger, interval_seconds=interval
        )
        self.monitor_worker.result_ready.connect(self.on_monitor_result)
        self.monitor_worker.outcome_ready.connect(self.on_monitor_outcome)
        self.monitor_worker.error_occurred.connect(self.on_monitor_error)
        self.monitor_worker.start()

        self.status.setText("🟢 ONLINE")
        self.status.setStyleSheet("font-size:16px;color:green;")

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        pair_names = "、".join(w["currency"] for w in enabled_pairs)
        self.add_log(f"監視開始（{interval}秒間隔 / 対象: {pair_names}）")

    def stop_monitor(self):
        if self.monitor_worker is not None:
            self.monitor_worker.stop()
            self.monitor_worker.wait()
            self.monitor_worker = None

        self.status.setText("🔴 OFFLINE")
        self.status.setStyleSheet("font-size:16px;color:red;")

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        self.add_log("監視停止")

    def closeEvent(self, event):
        """アプリ終了時に監視スレッドが動いていれば安全に停止する。"""
        if self.monitor_worker is not None:
            self.monitor_worker.stop()
            self.monitor_worker.wait()
            self.monitor_worker = None

        event.accept()

    # ==========================
    # 監視スレッドからのイベント
    # ==========================

    def on_monitor_result(self, result):
        """MonitorWorkerから新しい予想が届くたびに呼ばれる。"""
        self._handle_prediction(result, is_auto=True)

    def on_monitor_outcome(self, outcome):
        """MonitorWorkerから予想の正解/不正解が届くたびに呼ばれる。"""
        currency = outcome.get("currency", "")
        result_label = outcome.get("outcome", "UNKNOWN")

        self._update_prediction_row(currency, judgment=result_label)
        self._update_winrate_label()

        self.add_log(
            f"[判定] {currency}: {result_label} "
            f"(予想 {outcome.get('predicted_direction')} / "
            f"予想時価格 {outcome.get('predicted_price')} → "
            f"実際 {outcome.get('actual_price')})"
        )

    def on_monitor_error(self, message):
        """MonitorWorker内で想定外のエラーが起きた場合に呼ばれる。"""
        self.add_log(f"監視スレッドエラー: {message}")

    # ==========================
    # Settings
    # ==========================

    def open_settings(self):
        dialog = SettingsDialog(self.config)

        if dialog.exec():
            self.add_log("設定を保存しました")

    # ==========================
    # 手動キャプチャ（先頭の有効な通貨ペアのみ、その場で1回だけ解析）
    # ==========================

    def capture_screen(self):
        watch_list = self.config.get("watch_list", [])
        enabled_pairs = [w for w in watch_list if w.get("enabled", True)]

        if not enabled_pairs:
            self.add_log("監視する通貨ペアが設定されていません（Settingsで追加してください）")
            return

        item = enabled_pairs[0]
        currency = item["currency"]
        horizon = int(item.get("horizon_seconds", 20))
        keyword = Config.currency_to_keyword(currency)

        capture = ScreenCapture(window_keyword=keyword)
        capture_result = capture.capture()
        image_path = capture_result["path"]

        if capture_result["used_window_capture"]:
            self.add_log(f"{currency}: ウィンドウを検出してキャプチャしました")
        else:
            self.add_log(f"{currency}: ウィンドウが見つからず、画面全体をキャプチャしました")

        self.add_log(f"{currency}: AI解析中...")

        analysis = self.analyzer.analyze(image_path, horizon_seconds=horizon)

        combined = dict(analysis)
        combined["currency"] = currency
        combined["horizon_seconds"] = horizon
        combined["image_path"] = image_path
        combined["used_window_capture"] = capture_result["used_window_capture"]

        self._handle_prediction(combined, is_auto=False, log_to_history=True)

        self.add_log(
            "注意: 手動Captureでは、この予想が当たったかどうかの自動判定は行われません"
            "（自動判定はStart Monitorでの継続監視中のみ動作します）"
        )

    # ==========================
    # 予想結果の反映（共通処理）
    # ==========================

    def _handle_prediction(self, result, is_auto=False, log_to_history=False):
        """
        1件の予想結果をGUIに反映する。

        Args:
            result: analyzer.analyze()の結果 + currency / horizon_seconds /
                image_path / used_window_capture を含む辞書
            is_auto: MonitorWorker経由（自動監視）ならTrue
            log_to_history: Trueの場合、ここでTradeLoggerに記録する
                （MonitorWorker側は自身で記録済みなので、on_monitor_resultからはFalseで呼ぶ）
        """
        currency = result.get("currency", "-")
        image_path = result.get("image_path")

        if image_path:
            pixmap = QPixmap(image_path)
            self.chart_label.setPixmap(
                pixmap.scaled(
                    self.chart_label.width(),
                    self.chart_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

        prefix = "[自動] " if is_auto else ""

        if result.get("error"):
            self._update_prediction_row(currency, reason=f"エラー: {result['error']}")
            self.add_log(f"{prefix}{currency}: AI解析エラー: {result['error']}")
            return

        direction = result["direction"]
        confidence = result["confidence"]
        reason = result["reason"]
        horizon_seconds = result.get("horizon_seconds", 20)

        self._update_prediction_row(
            currency,
            direction=direction,
            confidence=confidence,
            reason=reason,
            judgment="判定待ち",
        )

        direction_label = "High" if direction == "HIGH" else "Low"

        self.add_log(
            f"{prefix}{currency}: {horizon_seconds}秒後 {direction_label} "
            f"予想（確信度 {confidence}%）"
        )

        if log_to_history:
            self.trade_logger.log(
                currency=currency,
                direction=direction,
                confidence=confidence,
                reason=reason,
                price=result.get("price"),
                horizon_seconds=horizon_seconds,
                image_path=image_path,
            )
            self._update_winrate_label()

        # ==========================
        # LINE通知
        # ==========================
        #
        # 監視間隔（数秒〜数十秒ごと）で毎回通知すると、
        # LINEの無料枠（月200通）をすぐに使い切ってしまうため、
        # 以下の両方を満たすときだけ通知する。
        #   1. Settingsの「最低Confidence」以上の予想である
        #   2. 前回そのペアで通知した方向（High/Low）から変わった
        #      （同じ方向が続く間は連続通知しない）

        min_confidence = int(self.config.get("confidence", 70))
        previous_direction = self._last_notified_direction.get(currency)

        should_notify = (
            self.config.get("notify_on_prediction", True)
            and confidence >= min_confidence
            and direction != previous_direction
        )

        if should_notify:
            bet_info = self.risk.calculate_max_loss()

            message = LineNotifier.build_signal_message(result)
            message += f"\n推奨ベット額目安: {bet_info['max_loss_amount']:,.0f}"

            # 注意: この呼び出しはLINEへの送信が完了するまでUIをブロックします。
            send_result = self.notifier.send(message)

            if send_result["success"]:
                self.add_log(f"{currency}: LINEに通知を送信しました")
                self._last_notified_direction[currency] = direction
            else:
                self.add_log(f"{currency}: LINE通知エラー: {send_result['error']}")

    def _update_prediction_row(
        self,
        currency,
        direction=None,
        confidence=None,
        reason=None,
        judgment=None,
    ):
        """
        予想一覧テーブルの、指定した通貨ペアの行を更新する。
        該当する行が無ければ新規に追加する。
        """
        row = None

        for r in range(self.predictions_table.rowCount()):
            item = self.predictions_table.item(r, 0)
            if item and item.text() == currency:
                row = r
                break

        if row is None:
            row = self.predictions_table.rowCount()
            self.predictions_table.insertRow(row)
            self.predictions_table.setItem(row, 0, QTableWidgetItem(currency))
            for col in range(1, 6):
                self.predictions_table.setItem(row, col, QTableWidgetItem(""))

        if direction is not None:
            label = "High" if direction == "HIGH" else ("Low" if direction == "LOW" else "-")
            self.predictions_table.setItem(row, 1, QTableWidgetItem(label))

        if confidence is not None:
            self.predictions_table.setItem(row, 2, QTableWidgetItem(f"{confidence}%"))

        if reason is not None:
            self.predictions_table.setItem(row, 3, QTableWidgetItem(reason))

        if judgment is not None:
            self.predictions_table.setItem(row, 4, QTableWidgetItem(judgment))

        now = datetime.now().strftime("%H:%M:%S")
        self.predictions_table.setItem(row, 5, QTableWidgetItem(now))

    def _update_winrate_label(self):
        """履歴から勝率を再計算し、勝率ラベルを更新する。"""
        stats = self.risk.calculate_win_rate(self.trade_logger.get_all())

        if stats["win_rate"] is None:
            self.winrate.setText(
                f"勝率 : - (0勝0敗 / 判定待ち{stats['pending']}件)"
            )
        else:
            self.winrate.setText(
                f"勝率 : {stats['win_rate']}% "
                f"({stats['wins']}勝{stats['losses']}敗 / 判定待ち{stats['pending']}件)"
            )
