"""
capture.py

IRIS Trade Assistant のキャプチャモジュール。

役割:
    TradingViewのウィンドウを自動検出してキャプチャする。
    ウィンドウが見つからない場合は、画面全体をキャプチャする
    （フォールバック）。

必要なパッケージ（Windows専用）:
    pip install pywin32
"""

from pathlib import Path
from datetime import datetime

from PIL import ImageGrab

try:
    import win32gui
except ImportError:
    win32gui = None


class ScreenCapture:
    """
    画面（またはTradingViewウィンドウ）をキャプチャして保存するクラス。

    Args:
        save_dir: 画像の保存先フォルダ（デフォルト: "captures"）
        window_keyword: 検出対象のウィンドウタイトルに含まれるキーワード
    """

    def __init__(self, save_dir: str = "captures", window_keyword: str = "TradingView"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)
        self.window_keyword = window_keyword

    # ==========================
    # 内部処理
    # ==========================

    def _find_target_window(self):
        """
        タイトルに window_keyword を含む、可視状態のウィンドウを探す。

        見つかった場合は hwnd（ウィンドウハンドル）を返す。
        見つからない場合、または pywin32 が使えない場合は None を返す。
        """
        if win32gui is None:
            return None

        matches = []

        def enum_handler(hwnd, _ctx):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            if title and self.window_keyword.lower() in title.lower():
                matches.append(hwnd)

        try:
            win32gui.EnumWindows(enum_handler, None)
        except Exception:
            return None

        return matches[0] if matches else None

    @staticmethod
    def _get_window_rect(hwnd):
        """
        ウィンドウの座標 (left, top, right, bottom) を取得する。

        最小化されている、または座標が異常な場合は None を返す。
        """
        try:
            rect = win32gui.GetWindowRect(hwnd)
        except Exception:
            return None

        left, top, right, bottom = rect

        # 最小化中や不正な座標（幅・高さが0以下）は除外
        if right - left <= 0 or bottom - top <= 0:
            return None

        return rect

    # ==========================
    # 公開メソッド
    # ==========================

    def capture(self) -> dict:
        """
        キャプチャを実行し、結果を辞書で返す。

        Returns:
            {
                "path": 保存した画像のパス（str）,
                "used_window_capture": TradingViewウィンドウを
                    検出してキャプチャできた場合 True、
                    画面全体にフォールバックした場合 False,
            }
        """
        used_window_capture = False

        hwnd = self._find_target_window()
        rect = self._get_window_rect(hwnd) if hwnd else None

        if rect is not None:
            try:
                image = ImageGrab.grab(bbox=rect)
                used_window_capture = True
            except Exception:
                image = ImageGrab.grab()
        else:
            image = ImageGrab.grab()

        filename = datetime.now().strftime("%Y%m%d_%H%M%S.png")
        filepath = self.save_dir / filename

        image.save(filepath)

        return {
            "path": str(filepath),
            "used_window_capture": used_window_capture,
        }
