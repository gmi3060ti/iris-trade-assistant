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
    QFileDialog,
)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("IRIS Trade Assistant")
        self.resize(700, 750)

        main_layout = QVBoxLayout()

        # ==========================
        # タイトル
        # ==========================
        title = QLabel("IRIS Trade Assistant")
        title.setStyleSheet("font-size:22px;font-weight:bold;")

        self.status = QLabel("🔴 OFFLINE")
        self.status.setStyleSheet("font-size:16px;color:red;")

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
        self.currency = QLabel("通貨 : EUR/USD")
        self.trend = QLabel("トレンド : WAIT")
        self.score = QLabel("スコア : 0 / 100")

        for w in (
            self.time_label,
            self.currency,
            self.trend,
            self.score,
        ):
            w.setStyleSheet("font-size:15px;")
            main_layout.addWidget(w)

        main_layout.addSpacing(10)

        # ==========================
        # チャート
        # ==========================
        chart_box = QGroupBox("📈 チャート")
        chart_layout = QVBoxLayout()

        self.chart_label = QLabel("チャート画像はここに表示されます")
        self.chart_label.setAlignment(Qt.AlignCenter)
        self.chart_label.setMinimumHeight(250)
        self.chart_label.setStyleSheet("""
            border:1px solid gray;
            border-radius:6px;
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

        for label in (
            self.ai_trend,
            self.ai_confidence,
            self.ai_recommendation,
        ):
            label.setStyleSheet("font-size:14px;")
            analysis_layout.addWidget(label)

        analysis_box.setLayout(analysis_layout)
        main_layout.addWidget(analysis_box)

        # ==========================
        # ボタン
        # ==========================
        self.start_btn = QPushButton("▶ Start Monitor")
        self.stop_btn = QPushButton("■ Stop")
        self.setting_btn = QPushButton("📂 Load Chart")

        self.start_btn.setMinimumHeight(40)
        self.stop_btn.setMinimumHeight(40)
        self.setting_btn.setMinimumHeight(40)

        main_layout.addWidget(self.start_btn)
        main_layout.addWidget(self.stop_btn)
        main_layout.addWidget(self.setting_btn)

        # ==========================
        # ログ
        # ==========================
        log_title = QLabel("ログ")

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        main_layout.addWidget(log_title)
        main_layout.addWidget(self.log)

        self.setLayout(main_layout)

        # ==========================
        # Signal
        # ==========================
        self.start_btn.clicked.connect(self.start_monitor)
        self.stop_btn.clicked.connect(self.stop_monitor)
        self.setting_btn.clicked.connect(self.load_chart)

        # ==========================
        # Timer
        # ==========================
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
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
        self.status.setText("🟢 ONLINE")
        self.status.setStyleSheet("font-size:16px;color:green;")
        self.add_log("監視開始")

    def stop_monitor(self):
        self.status.setText("🔴 OFFLINE")
        self.status.setStyleSheet("font-size:16px;color:red;")
        self.add_log("監視停止")

    def load_chart(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "チャート画像を選択",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )

        if file_path:
            pixmap = QPixmap(file_path)

            self.chart_label.setPixmap(
                pixmap.scaled(
                    self.chart_label.width(),
                    self.chart_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

            self.add_log("チャート画像を読み込みました")

            # 仮のAI分析結果
            self.ai_trend.setText("Trend : UP")
            self.ai_confidence.setText("Confidence : 82%")
            self.ai_recommendation.setText("Recommendation : BUY")