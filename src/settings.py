from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSpinBox,
    QPushButton,
)


class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("IRIS Settings")
        self.resize(400, 250)

        layout = QVBoxLayout()

        # 通貨ペア
        layout.addWidget(QLabel("通貨ペア"))

        self.currency = QComboBox()
        self.currency.addItems([
            "EUR/USD",
            "USD/JPY",
            "GBP/USD",
            "BTC/USD",
        ])
        layout.addWidget(self.currency)

        # AIモデル
        layout.addWidget(QLabel("AIモデル"))

        self.model = QComboBox()
        self.model.addItems([
            "GPT-5.5",
            "GPT-5",
            "Local AI",
        ])
        layout.addWidget(self.model)

        # 信頼度
        layout.addWidget(QLabel("最低Confidence"))

        self.confidence = QSpinBox()
        self.confidence.setRange(0, 100)
        self.confidence.setValue(70)
        self.confidence.setSuffix("%")
        layout.addWidget(self.confidence)

        # ボタン
        buttons = QHBoxLayout()

        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("キャンセル")

        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)

        layout.addLayout(buttons)

        self.setLayout(layout)