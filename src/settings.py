"""
settings.py

IRIS Trade Assistant の設定ダイアログ。

役割:
    通貨ペア・AIモデル・最低Confidence・API Key・
    LINE通知設定・リスク管理設定を編集するダイアログ。

    開いたときに Config から現在の値を読み込んで表示し、
    「保存」を押すと Config に書き戻して保存する。

    項目数が多いため、内容はスクロールエリアに収めている。
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QScrollArea,
    QWidget,
    QFrame,
)


class SettingsDialog(QDialog):
    """
    設定ダイアログ。

    Args:
        config: Config インスタンス。現在の設定の読み込み・保存に使う。
    """

    def __init__(self, config):
        super().__init__()

        self.config = config

        self.setWindowTitle("IRIS Settings")
        self.resize(420, 560)

        outer_layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        layout = QVBoxLayout()

        # ==========================
        # 通貨ペア
        # ==========================

        layout.addWidget(QLabel("通貨ペア"))

        self.currency = QComboBox()
        self.currency.addItems([
            "EUR/USD",
            "USD/JPY",
            "GBP/USD",
            "BTC/USD",
        ])
        layout.addWidget(self.currency)

        # ==========================
        # AIモデル
        # ==========================

        layout.addWidget(QLabel("AIモデル"))

        self.model = QComboBox()
        self.model.addItems([
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash",
        ])
        layout.addWidget(self.model)

        # ==========================
        # 信頼度
        # ==========================

        layout.addWidget(QLabel("最低Confidence"))

        self.confidence = QSpinBox()
        self.confidence.setRange(0, 100)
        self.confidence.setSuffix("%")
        layout.addWidget(self.confidence)

        # ==========================
        # API Key
        # ==========================

        layout.addWidget(QLabel("Gemini API Key"))

        api_key_row = QHBoxLayout()

        self.api_key = QLineEdit()
        self.api_key.setPlaceholderText("AIza...")
        self.api_key.setEchoMode(QLineEdit.Password)

        self.toggle_key_btn = QPushButton("表示")
        self.toggle_key_btn.setCheckable(True)
        self.toggle_key_btn.setMaximumWidth(60)
        self.toggle_key_btn.clicked.connect(self.toggle_key_visibility)

        api_key_row.addWidget(self.api_key)
        api_key_row.addWidget(self.toggle_key_btn)

        layout.addLayout(api_key_row)

        layout.addWidget(self._separator())

        # ==========================
        # LINE通知
        # ==========================

        layout.addWidget(QLabel("LINE Messaging API チャネルアクセストークン"))

        line_token_row = QHBoxLayout()

        self.line_token = QLineEdit()
        self.line_token.setPlaceholderText("チャネルアクセストークン（長期）")
        self.line_token.setEchoMode(QLineEdit.Password)

        self.toggle_line_token_btn = QPushButton("表示")
        self.toggle_line_token_btn.setCheckable(True)
        self.toggle_line_token_btn.setMaximumWidth(60)
        self.toggle_line_token_btn.clicked.connect(
            self.toggle_line_token_visibility
        )

        line_token_row.addWidget(self.line_token)
        line_token_row.addWidget(self.toggle_line_token_btn)

        layout.addLayout(line_token_row)

        self.notify_on_buy_sell = QCheckBox("BUY/SELL判断が出たらLINEに通知する")
        layout.addWidget(self.notify_on_buy_sell)

        layout.addWidget(self._separator())

        # ==========================
        # リスク管理
        # ==========================

        layout.addWidget(QLabel("口座残高"))

        self.account_balance = QDoubleSpinBox()
        self.account_balance.setRange(0, 1_000_000_000)
        self.account_balance.setDecimals(0)
        self.account_balance.setSingleStep(1000)
        layout.addWidget(self.account_balance)

        layout.addWidget(QLabel("1トレードあたりのリスク許容率"))

        self.risk_percent = QDoubleSpinBox()
        self.risk_percent.setRange(0, 100)
        self.risk_percent.setSuffix("%")
        self.risk_percent.setSingleStep(0.5)
        layout.addWidget(self.risk_percent)

        layout.addWidget(QLabel("基準 損切り幅"))

        self.stop_loss_percent = QDoubleSpinBox()
        self.stop_loss_percent.setRange(0.1, 100)
        self.stop_loss_percent.setSuffix("%")
        self.stop_loss_percent.setSingleStep(0.1)
        layout.addWidget(self.stop_loss_percent)

        layout.addWidget(QLabel("基準 利確幅"))

        self.take_profit_percent = QDoubleSpinBox()
        self.take_profit_percent.setRange(0.1, 100)
        self.take_profit_percent.setSuffix("%")
        self.take_profit_percent.setSingleStep(0.1)
        layout.addWidget(self.take_profit_percent)

        content.setLayout(layout)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

        # ==========================
        # ボタン（スクロールエリアの外に固定）
        # ==========================

        buttons = QHBoxLayout()

        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("キャンセル")

        save_btn.clicked.connect(self.save_and_accept)
        cancel_btn.clicked.connect(self.reject)

        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)

        outer_layout.addLayout(buttons)

        self.setLayout(outer_layout)

        # 現在の設定値を各項目に反映
        self.load_from_config()

    # ==========================
    # 内部処理
    # ==========================

    @staticmethod
    def _separator():
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        return line

    def load_from_config(self):
        """Config の現在値をダイアログの各項目に反映する。"""
        self.currency.setCurrentText(
            self.config.get("currency", "EUR/USD")
        )
        self.model.setCurrentText(
            self.config.get("ai_model", "gemini-3.5-flash")
        )
        self.confidence.setValue(
            self.config.get("confidence", 70)
        )
        self.api_key.setText(
            self.config.get("api_key", "")
        )
        self.line_token.setText(
            self.config.get("line_channel_access_token", "")
        )
        self.notify_on_buy_sell.setChecked(
            bool(self.config.get("notify_on_buy_sell", True))
        )
        self.account_balance.setValue(
            float(self.config.get("account_balance", 100000))
        )
        self.risk_percent.setValue(
            float(self.config.get("risk_percent", 2.0))
        )
        self.stop_loss_percent.setValue(
            float(self.config.get("stop_loss_percent", 1.0))
        )
        self.take_profit_percent.setValue(
            float(self.config.get("take_profit_percent", 2.0))
        )

    def toggle_key_visibility(self):
        """API Keyの表示・非表示を切り替える。"""
        if self.toggle_key_btn.isChecked():
            self.api_key.setEchoMode(QLineEdit.Normal)
            self.toggle_key_btn.setText("隠す")
        else:
            self.api_key.setEchoMode(QLineEdit.Password)
            self.toggle_key_btn.setText("表示")

    def toggle_line_token_visibility(self):
        """LINEチャネルアクセストークンの表示・非表示を切り替える。"""
        if self.toggle_line_token_btn.isChecked():
            self.line_token.setEchoMode(QLineEdit.Normal)
            self.toggle_line_token_btn.setText("隠す")
        else:
            self.line_token.setEchoMode(QLineEdit.Password)
            self.toggle_line_token_btn.setText("表示")

    def save_and_accept(self):
        """入力内容を Config に書き戻して保存し、ダイアログを閉じる。"""
        self.config.update({
            "currency": self.currency.currentText(),
            "ai_model": self.model.currentText(),
            "confidence": self.confidence.value(),
            "api_key": self.api_key.text(),
            "line_channel_access_token": self.line_token.text(),
            "notify_on_buy_sell": self.notify_on_buy_sell.isChecked(),
            "account_balance": self.account_balance.value(),
            "risk_percent": self.risk_percent.value(),
            "stop_loss_percent": self.stop_loss_percent.value(),
            "take_profit_percent": self.take_profit_percent.value(),
        })
        self.config.save()

        self.accept()
