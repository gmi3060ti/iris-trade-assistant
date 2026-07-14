"""
analyzer.py

IRIS Trade Assistant の解析モジュール。

役割:
    キャプチャしたチャート画像を Google Gemini API（画像入力対応）に送信し、
    「N秒後にHigh（上昇）かLow（下落）か」を予想させる。
    あわせて、画面に表示されている現在価格の読み取りも行う
    （読み取れた価格は、後で予想が当たったかどうかを
      自動判定するときに使う）。

使い方:
    from config import Config
    from analyzer import Analyzer

    config = Config()
    analyzer = Analyzer(config)

    result = analyzer.analyze("captures/20260710_120000.png", horizon_seconds=20)

    print(result["direction"])   # "HIGH" / "LOW"
    print(result["confidence"])  # 0-100
    print(result["reason"])      # 判断理由の説明文
    print(result["price"])       # 読み取れた現在価格（float）。読めなければ None
    print(result["error"])       # 失敗時のみ。成功時は None

必要なパッケージ:
    pip install google-genai

API Keyの取得（無料）:
    https://aistudio.google.com/ の「Get API key」から取得できます。
    クレジットカードの登録は不要です（無料枠には利用回数の上限があります）。

注意（重要）:
    短い時間軸（数十秒程度）での値動きの予想は、静止画のチャートから
    高い精度で当てられるようなものではありません。実際にどれくらい
    当たるかは、logger.py に記録される勝敗の実績を見て判断してください。
"""

import json
from pathlib import Path

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


def _build_system_prompt(horizon_seconds: int) -> str:
    """予想の時間軸（秒）を埋め込んだシステムプロンプトを組み立てる。"""
    return f"""あなたはFXおよび仮想通貨チャートを解析するトレードアシスタントです。
渡されたチャート画像を分析し、「今から{horizon_seconds}秒後に価格がHigh（上昇）に
なっているかLow（下落）になっているか」を予想してください。

## 分析の手順

判断する前に、画像から読み取れる以下の要素を具体的に検討してください。

1. **直近のローソク足の勢い**: 直近数本の実体（始値〜終値の幅）が大きいか小さいか。
   大陽線・大陰線が連続しているか、それとも小さい実体が並んでいるか
2. **トレンドの方向と強さ**: 直近の高値・安値が切り上がっているか切り下がっているか。
   横ばい（レンジ）に見えるか
3. **直近の値動きの位置**: 直近のサポート/レジスタンスや移動平均線（表示されていれば）に
   近いか、そこから離れているか
4. **ノイズの多さ**: 上下に激しく行ったり来たりしている（予測しづらい）か、
   一方向になめらかに動いている（予測しやすい）か

## 確信度（confidence）の基準

上記の検討結果に応じて、以下の基準を目安に0〜100の整数で答えてください。
**根拠が弱い場合に無難な数値（50前後）へ逃げず、実際に検討した内容に応じて
数値を大きく振ってください。**

- 80〜100: 直近のローソク足の勢いとトレンドの方向がはっきり一致しており、
  ノイズが少なく方向感が明確
- 60〜79: ある程度の方向感はあるが、勢いが弱い、またはやや迷いが見える
- 40〜59: 方向感が読み取りにくい、レンジ相場、または上下の材料が拮抗している
- 0〜39: ほぼ判断材料が無い、または相反する材料が強く、五分五分に近い

## 出力形式

また、画面に表示されている現在価格（数値）も、可能な範囲で読み取ってください。
読み取れない場合は null にしてください。

以下のJSON形式のみで回答してください。
説明文やMarkdownの装飾（```json など）は一切含めないでください。

{{
  "direction": "HIGH" または "LOW",
  "confidence": 0から100の整数（上記の基準に沿って算出）,
  "reason": "上記1〜4のうち、判断の決め手になった具体的な観察を日本語で1〜2文で",
  "price": 画面に表示されている現在価格（数値）。読み取れなければ null
}}
"""


# 価格だけを読み取る際に使うシステムプロンプト（read_price用）
_PRICE_ONLY_SYSTEM_PROMPT = """あなたはFX/仮想通貨チャート画面から、
現在表示されている価格を読み取るアシスタントです。

画像に表示されている現在価格（数値）を読み取り、
以下のJSON形式のみで回答してください。
説明文やMarkdownの装飾（```json など）は一切含めないでください。

{
  "price": 現在価格（数値）。読み取れなければ null
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
    "direction": None,
    "confidence": 0,
    "reason": "",
    "price": None,
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
    def _load_image_bytes(image_path: str) -> tuple:
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

        direction = str(data.get("direction", "")).upper()
        if direction not in ("HIGH", "LOW"):
            direction = None

        raw_price = data.get("price", None)
        try:
            price = float(raw_price) if raw_price is not None else None
        except (TypeError, ValueError):
            price = None

        result = _EMPTY_RESULT.copy()
        result["direction"] = direction
        result["confidence"] = int(data.get("confidence", 0))
        result["reason"] = str(data.get("reason", ""))
        result["price"] = price
        result["error"] = None

        return result

    # ==========================
    # 公開メソッド
    # ==========================

    def analyze(self, image_path: str, horizon_seconds: int = 20) -> dict:
        """
        チャート画像を解析し、結果を辞書で返す。

        Args:
            image_path: 解析するチャート画像のパス
            horizon_seconds: 何秒後の値動きを予想させるか

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

        model = self.config.get("ai_model", "gemini-3.1-flash-lite")
        system_prompt = _build_system_prompt(horizon_seconds)

        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    f"このチャート画像を解析し、{horizon_seconds}秒後の値動きを予想してください。",
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
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

        if parsed["direction"] is None:
            parsed["error"] = (
                "AIの返答からHIGH/LOWを読み取れませんでした。"
            )

        return parsed

    def read_price(self, image_path: str) -> dict:
        """
        チャート画像から、現在表示されている価格だけを読み取る
        （方向性の予想は行わない）。

        予想が的中したかどうかを後から自動判定する（resolve_outcome）際、
        期限が来た予想の「実際の価格」を取得するために使う。

        Returns:
            {"price": float または None, "error": str または None}
        """
        if not Path(image_path).exists():
            return {"price": None, "error": f"画像ファイルが見つかりません: {image_path}"}

        try:
            client = self._get_client()
        except RuntimeError as e:
            return {"price": None, "error": str(e)}

        try:
            image_bytes, mime_type = self._load_image_bytes(image_path)
        except OSError as e:
            return {"price": None, "error": f"画像の読み込みに失敗しました: {e}"}

        model = self.config.get("ai_model", "gemini-3.1-flash-lite")

        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    "この画像に表示されている現在価格を読み取ってください。",
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                ],
                config=types.GenerateContentConfig(
                    system_instruction=_PRICE_ONLY_SYSTEM_PROMPT,
                ),
            )

            text = response.text

        except Exception as e:
            return {"price": None, "error": f"価格読み取りに失敗しました: {e}"}

        if not text:
            return {"price": None, "error": "AIから空の返答が返されました。"}

        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                if cleaned.endswith("```"):
                    cleaned = cleaned.rsplit("```", 1)[0]
                cleaned = cleaned.strip()

            data = json.loads(cleaned)
            raw_price = data.get("price", None)
            price = float(raw_price) if raw_price is not None else None

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            return {"price": None, "error": f"AIの返答を解釈できませんでした: {e}"}

        return {"price": price, "error": None}


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

    print(analyzer.analyze(image_arg, horizon_seconds=20))