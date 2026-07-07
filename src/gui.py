from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("IRIS Trade Assistant")
        self.resize(550, 520)

        main_layout = QVBoxLayout()

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

        main_layout.addSpacing(15)

        self.start_btn = QPushButton("▶ Start Monitor")
        self.stop_btn = QPushButton("■ Stop")
        self.setting_btn = QPushButton("⚙ Settings")

        self.start_btn.setMinimumHeight(40)
        self.stop_btn.setMinimumHeight(40)
        self.setting_btn.setMinimumHeight(40)

        main_layout.addWidget(self.start_btn)
        main_layout.addWidget(self.stop_btn)
        main_layout.addWidget(self.setting_btn)

        main_layout.addSpacing(15)

        log_title = QLabel("ログ")
        log_title.setStyleSheet("font-size:16px;font-weight:bold;")

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        main_layout.addWidget(log_title)
        main_layout.addWidget(self.log)

        self.setLayout(main_layout)

        self.start_btn.clicked.connect(self.start_monitor)
        self.stop_btn.clicked.connect(self.stop_monitor)

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