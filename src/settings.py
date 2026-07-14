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
    QTableWidget,
    QTableWidgetItem,
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
        # 監視する通貨ペア（複数）
        # ==========================

        layout.addWidget(QLabel("監視する通貨ペア"))

        add_row = QHBoxLayout()

        self.new_currency = QComboBox()
        self.new_currency.addItems([
            "EUR/USD",
            "USD/JPY",
            "GBP/USD",
            "BTC/USD",
        ])

        self.new_horizon = QSpinBox()
        self.new_horizon.setRange(5, 300)
        self.new_horizon.setValue(20)
        self.new_horizon.setSuffix("秒後")

        add_btn = QPushButton("追加")
        add_btn.clicked.connect(self.add_watch_item)

        add_row.addWidget(self.new_currency)
        add_row.addWidget(self.new_horizon)
        add_row.addWidget(add_btn)

        layout.addLayout(add_row)

        self.watch_table = QTableWidget(0, 3)
        self.watch_table.setHorizontalHeaderLabels(
            ["通貨ペア", "時間軸(秒)", "有効"]
        )
        self.watch_table.horizontalHeader().setStretchLastSection(True)
        self.watch_table.setMinimumHeight(150)
        layout.addWidget(self.watch_table)

        remove_btn = QPushButton("選択した行を削除")
        remove_btn.clicked.connect(self.remove_selected_watch_item)
        layout.addWidget(remove_btn)

        layout.addWidget(self._separator())

        # ==========================
        # AIモデル
        # ==========================

        layout.addWidget(QLabel("AIモデル"))

        self.model = QComboBox()
        self.model.addItems([
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash",
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

        self.notify_on_prediction = QCheckBox(
            "最低Confidence以上の予想が出たらLINEに通知する"
        )
        layout.addWidget(self.notify_on_prediction)

        layout.addWidget(self._separator())

        # ==========================
        # 資金管理（推奨ベット額）
        # ==========================

        layout.addWidget(QLabel("口座残高"))

        self.account_balance = QDoubleSpinBox()
        self.account_balance.setRange(0, 1_000_000_000)
        self.account_balance.setDecimals(0)
        self.account_balance.setSingleStep(1000)
        layout.addWidget(self.account_balance)

        layout.addWidget(QLabel("1回の予想あたりのリスク許容率（推奨ベット額の計算に使用）"))

        self.risk_percent = QDoubleSpinBox()
        self.risk_percent.setRange(0, 100)
        self.risk_percent.setSuffix("%")
        self.risk_percent.setSingleStep(0.5)
        layout.addWidget(self.risk_percent)

        layout.addWidget(self._separator())

        # ==========================
        # 定期監視の間隔
        # ==========================

        layout.addWidget(QLabel("定期監視の間隔"))

        self.monitor_interval = QSpinBox()
        self.monitor_interval.setRange(3, 300)
        self.monitor_interval.setSuffix("秒")
        layout.addWidget(self.monitor_interval)

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

    def add_watch_item(self):
        """入力欄の内容で、監視リストに新しい行を追加する。"""
        currency = self.new_currency.currentText()
        horizon = self.new_horizon.value()
        self._add_watch_row(currency, horizon, True)

    def _add_watch_row(self, currency: str, horizon_seconds: int, enabled: bool):
        """監視リストのテーブルに1行追加する。"""
        row = self.watch_table.rowCount()
        self.watch_table.insertRow(row)

        self.watch_table.setItem(row, 0, QTableWidgetItem(currency))
        self.watch_table.setItem(row, 1, QTableWidgetItem(str(horizon_seconds)))

        enabled_checkbox = QCheckBox()
        enabled_checkbox.setChecked(enabled)
        self.watch_table.setCellWidget(row, 2, enabled_checkbox)

    def remove_selected_watch_item(self):
        """選択されている行を監視リストから削除する。"""
        selected_rows = sorted(
            {index.row() for index in self.watch_table.selectedIndexes()},
            reverse=True,
        )
        for row in selected_rows:
            self.watch_table.removeRow(row)

    def _collect_watch_list(self) -> list:
        """監視リストのテーブルの内容を、config保存用のリストにまとめる。"""
        watch_list = []

        for row in range(self.watch_table.rowCount()):
            currency_item = self.watch_table.item(row, 0)
            horizon_item = self.watch_table.item(row, 1)
            enabled_widget = self.watch_table.cellWidget(row, 2)

            currency = currency_item.text() if currency_item else ""

            try:
                horizon_seconds = int(horizon_item.text()) if horizon_item else 20
            except ValueError:
                horizon_seconds = 20

            enabled = enabled_widget.isChecked() if enabled_widget else True

            if currency:
                watch_list.append({
                    "currency": currency,
                    "horizon_seconds": horizon_seconds,
                    "enabled": enabled,
                })

        return watch_list

    def load_from_config(self):
        """Config の現在値をダイアログの各項目に反映する。"""
        self.watch_table.setRowCount(0)

        for item in self.config.get("watch_list", []):
            self._add_watch_row(
                item.get("currency", ""),
                item.get("horizon_seconds", 20),
                item.get("enabled", True),
            )

        self.model.setCurrentText(
            self.config.get("ai_model", "gemini-3.1-flash-lite")
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
        self.notify_on_prediction.setChecked(
            bool(self.config.get("notify_on_prediction", True))
        )
        self.account_balance.setValue(
            float(self.config.get("account_balance", 100000))
        )
        self.risk_percent.setValue(
            float(self.config.get("risk_percent", 2.0))
        )
        self.monitor_interval.setValue(
            int(self.config.get("monitor_interval_seconds", 5))
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
            "watch_list": self._collect_watch_list(),
            "ai_model": self.model.currentText(),
            "confidence": self.confidence.value(),
            "api_key": self.api_key.text(),
            "line_channel_access_token": self.line_token.text(),
            "notify_on_prediction": self.notify_on_prediction.isChecked(),
            "account_balance": self.account_balance.value(),
            "risk_percent": self.risk_percent.value(),
            "monitor_interval_seconds": self.monitor_interval.value(),
        })
        self.config.save()

        self.accept()
