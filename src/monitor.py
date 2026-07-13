"""
monitor.py

IRIS Trade Assistant の定期監視モジュール。

役割:
    一定間隔（デフォルト5秒）でチャートのキャプチャとAI解析を
    バックグラウンドスレッドで繰り返し実行する。

    GUIの操作をブロックしないよう QThread 上で実行し、
    結果は Qt のシグナル経由でメインスレッド（GUI）に通知する。

使い方:
    from monitor import MonitorWorker

    worker = MonitorWorker(capture, analyzer, interval_seconds=5)
    worker.result_ready.connect(on_result)   # dict を受け取るスロット
    worker.error_occurred.connect(on_error)  # str を受け取るスロット
    worker.start()

    # 停止する場合
    worker.stop()
    worker.wait()  # スレッドの終了を待つ（必要な場合）
"""

from PySide6.QtCore import QThread, Signal


class MonitorWorker(QThread):
    """
    バックグラウンドで定期的にキャプチャ＋AI解析を行うワーカースレッド。

    Args:
        capture: ScreenCapture インスタンス
        analyzer: Analyzer インスタンス
        interval_seconds: 解析の実行間隔（秒）。デフォルト5秒。
    """

    # 解析が1回完了するたびに発行される。
    # 中身は capture_screen() が使っているのと同じキー構成の辞書。
    result_ready = Signal(dict)

    # ワーカー内で予期しない例外が起きた場合に発行される。
    # （analyzer / capture 自体は失敗をresult内のerrorキーで返す設計なので、
    #  これは主にそれ以外の想定外エラー向け）
    error_occurred = Signal(str)

    def __init__(self, capture, analyzer, interval_seconds: int = 5):
        super().__init__()
        self.capture = capture
        self.analyzer = analyzer
        self.interval_seconds = interval_seconds
        self._running = False

    def run(self):
        """スレッドのメイン処理。stop() が呼ばれるまでループする。"""
        self._running = True

        while self._running:
            try:
                capture_result = self.capture.capture()
                image_path = capture_result["path"]

                analysis = self.analyzer.analyze(image_path)

                combined = dict(analysis)
                combined["image_path"] = image_path
                combined["used_window_capture"] = capture_result["used_window_capture"]

                self.result_ready.emit(combined)

            except Exception as e:
                # capture/analyzer側で捕捉しきれなかった想定外のエラー
                self.error_occurred.emit(str(e))

            # interval_seconds分待機する。
            # stop()が呼ばれたら早めにループを抜けられるよう、
            # 100ms刻みでフラグをチェックする。
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
        現在の待機・処理が終わり次第ループを抜ける（最大で待機の途中まで進む）。
        確実にスレッド終了を待ちたい場合は、呼び出し側で wait() すること。
        """
        self._running = False
