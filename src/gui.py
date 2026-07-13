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

        self.setWindowTitle("IRIS Trade Assistant β1")
        self.resize(800, 820)

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

        self.currency = QLabel(
            f"通貨 : {self.config.get('currency', 'EUR/USD')}"
        )

        self.trend = QLabel(
            "トレンド : WAIT"
        )

        self.score = QLabel(
            "スコア : 0 / 100"
        )

        self.winrate = QLabel(
            "勝率 : - (0勝0敗 / 判定待ち0件)"
        )

        for widget in (
            self.time_label,
            self.currency,
            self.trend,
            self.score,
            self.winrate,
        ):
            widget.setStyleSheet(
                "font-size:15px;"
            )

            main_layout.addWidget(widget)

        main_layout.addSpacing(10)

        # ==========================
        # チャート
        # ==========================

        chart_box = QGroupBox("📈 Chart")

        chart_layout = QVBoxLayout()

        self.chart_label = QLabel(
            "キャプチャ画像がここに表示されます"
        )

        self.chart_label.setAlignment(
            Qt.AlignCenter
        )

        self.chart_label.setMinimumHeight(300)

        self.chart_label.setStyleSheet("""
            border:1px solid gray;
            border-radius:8px;
            background:#2b2b2b;
        """)

        chart_layout.addWidget(self.chart_label)

        chart_box.setLayout(chart_layout)

        main_layout.addWidget(chart_box)
        
        # ==========================
        # AI Analysis
        # ==========================

        analysis_box = QGroupBox("🤖 AI Analysis")

        analysis_layout = QVBoxLayout()

        self.ai_trend = QLabel("Trend : WAIT")
        self.ai_confidence = QLabel("Confidence : 0%")
        self.ai_recommendation = QLabel("Recommendation : -")
        self.ai_reason = QLabel("Reason : -")
        self.ai_reason.setWordWrap(True)

        for widget in (
            self.ai_trend,
            self.ai_confidence,
            self.ai_recommendation,
            self.ai_reason,
        ):
            widget.setStyleSheet("font-size:14px;")
            analysis_layout.addWidget(widget)

        analysis_box.setLayout(analysis_layout)

        main_layout.addWidget(analysis_box)

        main_layout.addSpacing(10)

        # ==========================
        # ボタン
        # ==========================

        self.start_btn = QPushButton("▶ Start Monitor")
        self.stop_btn = QPushButton("■ Stop")
        self.capture_btn = QPushButton("📸 Capture")
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

        self.add_log("IRIS 起動")
        self.add_log("待機中...")

    def update_time(self):
        now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        self.time_label.setText(f"現在時刻 : {now}")

    def add_log(self, message):
        now = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{now}] {message}")

    def start_monitor(self):
        if self.monitor_worker is not None:
            return  # すでに監視中

        capture = ScreenCapture()

        self.monitor_worker = MonitorWorker(
            capture, self.analyzer, interval_seconds=5
        )
        self.monitor_worker.result_ready.connect(self.on_monitor_result)
        self.monitor_worker.error_occurred.connect(self.on_monitor_error)
        self.monitor_worker.start()

        self.status.setText("🟢 ONLINE")
        self.status.setStyleSheet("font-size:16px;color:green;")

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.add_log("監視開始（5秒ごとに自動解析）")

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

    def on_monitor_result(self, result):
        """MonitorWorkerから結果が届くたびに呼ばれる（メインスレッド上で実行）。"""
        self._display_result(result, is_auto=True)

    def on_monitor_error(self, message):
        """MonitorWorker内で想定外のエラーが起きた場合に呼ばれる。"""
        self.add_log(f"監視スレッドエラー: {message}")

    def closeEvent(self, event):
        """アプリ終了時に監視スレッドが動いていれば安全に停止する。"""
        if self.monitor_worker is not None:
            self.monitor_worker.stop()
            self.monitor_worker.wait()
            self.monitor_worker = None

        event.accept()

    def open_settings(self):
        dialog = SettingsDialog(self.config)

        if dialog.exec():
            self.currency.setText(
                f"通貨 : {self.config.get('currency')}"
            )

            self.add_log("設定を保存しました")

    def capture_screen(self):
        capture = ScreenCapture()

        capture_result = capture.capture()
        image_path = capture_result["path"]

        if capture_result["used_window_capture"]:
            self.add_log("TradingViewウィンドウを検出してキャプチャしました")
        else:
            self.add_log("TradingViewウィンドウが見つからず、画面全体をキャプチャしました")

        self.add_log("AI解析中...")

        analysis = self.analyzer.analyze(image_path)

        combined = dict(analysis)
        combined["image_path"] = image_path
        combined["used_window_capture"] = capture_result["used_window_capture"]

        self._display_result(combined)

    def _display_result(self, result, is_auto=False):
        """
        解析結果をGUIに反映する。

        手動Capture（capture_screen）と自動監視（on_monitor_result）の
        両方から呼ばれる共通処理。
        """
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

        if result["error"]:
            self.ai_trend.setText("Trend : -")
            self.ai_confidence.setText("Confidence : -")
            self.ai_recommendation.setText("Recommendation : -")
            self.ai_reason.setText("Reason : -")

            self.add_log(f"{prefix}AI解析エラー: {result['error']}")
            return

        self.ai_trend.setText(f"Trend : {result['trend']}")
        self.ai_confidence.setText(f"Confidence : {result['confidence']}%")
        self.ai_recommendation.setText(
            f"Recommendation : {result['recommendation']}"
        )
        self.ai_reason.setText(f"Reason : {result['reason']}")

        # 画面上部のトレンド表示にも反映
        self.trend.setText(f"トレンド : {result['recommendation']}")
        self.score.setText(f"スコア : {result['confidence']} / 100")

        self.add_log(
            f"{prefix}AI解析完了: {result['recommendation']} "
            f"(Confidence {result['confidence']}%)"
        )

        # ==========================
        # リスク目安の計算
        # ==========================

        risk_levels = self.risk.suggest_risk_levels(
            result["recommendation"], result["confidence"]
        )

        if result["recommendation"] in ("BUY", "SELL"):
            self.add_log(
                f"目安 損切り: -{risk_levels['stop_loss_percent']}% "
                f"/ 利確: +{risk_levels['take_profit_percent']}% "
                f"(リスクリワード比 1:{risk_levels['risk_reward_ratio']})"
            )

        # ==========================
        # 履歴保存
        # ==========================

        self.trade_logger.log(
            currency=self.config.get("currency"),
            trend=result["trend"],
            confidence=result["confidence"],
            recommendation=result["recommendation"],
            reason=result["reason"],
            image_path=image_path,
            stop_loss_percent=risk_levels["stop_loss_percent"],
            take_profit_percent=risk_levels["take_profit_percent"],
        )

        self._update_winrate_label()

        # ==========================
        # LINE通知（BUY/SELL時のみ）
        # ==========================

        if (
            result["recommendation"] in ("BUY", "SELL")
            and self.config.get("notify_on_buy_sell", True)
        ):
            message = LineNotifier.build_signal_message(
                self.config.get("currency"),
                {**result, **risk_levels},
            )

            # 注意: この呼び出しはLINEへの送信が完了するまでUIをブロックします。
            send_result = self.notifier.send(message)

            if send_result["success"]:
                self.add_log("LINEに通知を送信しました")
            else:
                self.add_log(f"LINE通知エラー: {send_result['error']}")

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