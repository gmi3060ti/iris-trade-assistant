"""
analyzer.py

IRIS Trade Assistant の解析モジュール。

役割:
    キャプチャしたチャート画像を Google Gemini API（画像入力対応）に送信し、
    トレンド・信頼度・売買判断・理由を取得する。

使い方:
    from config import Config
    from analyzer import Analyzer

    config = Config()
    analyzer = Analyzer(config)

    result = analyzer.analyze("captures/20260710_120000.png")

    print(result["trend"])          # "UP" / "DOWN" / "FLAT"
    print(result["confidence"])     # 0-100
    print(result["recommendation"]) # "BUY" / "SELL" / "WAIT"
    print(result["reason"])         # 判断理由の説明文
    print(result["error"])          # 失敗時のみ。成功時は None

必要なパッケージ:
    pip install google-genai

API Keyの取得（無料）:
    https://aistudio.google.com/ の「Get API key」から取得できます。
    クレジットカードの登録は不要です（無料枠には利用回数の上限があります）。
"""

import json
from pathlib import Path

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


# モデルへの指示文（システムプロンプト）
SYSTEM_PROMPT = """あなたはFXおよび仮想通貨チャートを解析するトレードアシスタントです。
渡されたチャート画像を分析し、以下のJSON形式のみで回答してください。
説明文やMarkdownの装飾（```json など）は一切含めないでください。

{
  "trend": "UP" または "DOWN" または "FLAT",
  "confidence": 0から100の整数（判断の確信度）,
  "recommendation": "BUY" または "SELL" または "WAIT",
  "reason": "判断理由を日本語で1〜2文で簡潔に"
}
"""

# 画像拡張子ごとのMIMEタイプ
_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

# 失敗時に返す既定値
_EMPTY_RESULT = {
    "trend": "WAIT",
    "confidence": 0,
    "recommendation": "WAIT",
    "reason": "",
    "error": None,
}


class Analyzer:
    """
    チャート画像をAIで解析するクラス（Gemini API使用）。

    Args:
        config: Config インスタンス。api_key / ai_model / confidence を参照する。
    """

    def __init__(self, config):
        self.config = config
        self._client = None

    # ==========================
    # 内部処理
    # ==========================

    def _get_client(self):
        """Geminiクライアントを取得する（初回のみ生成）。"""
        if genai is None:
            raise RuntimeError(
                "google-genai パッケージがインストールされていません。"
                "`pip install google-genai` を実行してください。"
            )

        if self._client is None:
            api_key = self.config.get("api_key", "")

            if not api_key:
                raise RuntimeError(
                    "API Keyが設定されていません。Settings画面から設定してください。"
                    "（https://aistudio.google.com/ で無料取得できます）"
                )

            self._client = genai.Client(api_key=api_key)

        return self._client

    @staticmethod
    def _load_image_bytes(image_path: str) -> tuple[bytes, str]:
        """画像ファイルをバイト列として読み込み、MIMEタイプと一緒に返す。"""
        path = Path(image_path)
        mime_type = _MIME_TYPES.get(path.suffix.lower(), "image/png")

        with open(path, "rb") as f:
            return f.read(), mime_type

    @staticmethod
    def _parse_response(text: str) -> dict:
        """
        モデルの返答テキストからJSONを取り出してパースする。

        モデルが ```json ... ``` のようにコードブロックで
        囲んで返してきた場合にも対応する。
        """
        cleaned = text.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

        data = json.loads(cleaned)

        result = _EMPTY_RESULT.copy()
        result["trend"] = str(data.get("trend", "WAIT")).upper()
        result["confidence"] = int(data.get("confidence", 0))
        result["recommendation"] = str(data.get("recommendation", "WAIT")).upper()
        result["reason"] = str(data.get("reason", ""))
        result["error"] = None

        return result

    # ==========================
    # 公開メソッド
    # ==========================

    def analyze(self, image_path: str) -> dict:
        """
        チャート画像を解析し、結果を辞書で返す。

        失敗した場合も例外は投げず、result["error"] にメッセージを入れて返す。
        （呼び出し側のGUIをクラッシュさせないため）
        """
        result = _EMPTY_RESULT.copy()

        if not Path(image_path).exists():
            result["error"] = f"画像ファイルが見つかりません: {image_path}"
            return result

        try:
            client = self._get_client()
        except RuntimeError as e:
            result["error"] = str(e)
            return result

        try:
            image_bytes, mime_type = self._load_image_bytes(image_path)
        except OSError as e:
            result["error"] = f"画像の読み込みに失敗しました: {e}"
            return result

        model = self.config.get("ai_model", "gemini-3.5-flash")

        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    "このチャート画像を解析してください。",
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                ],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                ),
            )

            text = response.text

        except Exception as e:
            # APIキー不正、レート制限超過、ネットワークエラーなど
            result["error"] = f"AI解析に失敗しました: {e}"
            return result

        if not text:
            result["error"] = "AIから空の返答が返されました。"
            return result

        try:
            parsed = self._parse_response(text)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            result["error"] = f"AIの返答を解釈できませんでした: {e}"
            return result

        return parsed


if __name__ == "__main__":
    # 簡易動作確認（実際にAPIを呼び出すには config.json に api_key が必要）
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from config import Config

    cfg = Config()
    analyzer = Analyzer(cfg)

    if len(sys.argv) > 1:
        image_arg = sys.argv[1]
    else:
        image_arg = "captures/sample.png"

    print(analyzer.analyze(image_arg))
