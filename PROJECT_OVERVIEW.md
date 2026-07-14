# IRIS Trade Assistant 開発要約（2026年7月時点）

## プロジェクト概要

**プロジェクト名**: IRIS Trade Assistant

**目的**: TradingViewのチャートをAIで解析し、複数の通貨ペアについて
「N秒後にHigh（上昇）かLow（下落）か」を予想し、LINEに通知するWindowsデスクトップアプリ。

**開発言語**: Python 3.13
**GUI**: PySide6
**AI**: Google Gemini API（`google-genai`パッケージ、無料枠を利用）
**通知**: LINE Messaging API（Broadcast方式）
**開発環境**: VS Code / Windows 11 / GitHub

---

## 現在のフォルダ構成

```
iris-trade-assistant/
├── README.md
├── PROJECT_OVERVIEW.md   ← このファイル
├── .gitignore
├── src/
│   ├── main.py           起動処理
│   ├── gui.py             メイン画面（通貨ペアごとの予想一覧を表示）
│   ├── capture.py         TradingViewウィンドウの自動検出＋キャプチャ
│   ├── analyzer.py        Gemini APIでHigh/Low予想＋価格読み取り
│   ├── monitor.py         複数通貨ペアの定期監視スレッド（自動判定つき）
│   ├── config.py          設定の保存・読み込み（config.json）
│   ├── settings.py        設定ダイアログ（通貨ペア一覧、AIモデル、LINE設定など）
│   ├── logger.py          予想履歴の保存・自動判定（history.json）
│   ├── notification.py    LINE通知（Messaging API / Broadcast）
│   ├── scoring.py         推奨ベット額・勝率の集計
│   ├── widgets.py         未使用（今後の拡張用）
│   └── styles.py          ダークテーマのQSSスタイル
```

`config.json` と `history.json` は `.gitignore` に入っており、
APIキーなどの秘密情報を含むため **Gitにはコミットされません**。

---

## GitHub

https://github.com/gmi3060ti/iris-trade-assistant

`git add . / git commit / git push` で管理。

**重要**: `config.json` は絶対にコミットしないこと（APIキー・LINEトークンが入っている）。
過去に一度誤ってコミットしてしまい、GitHubのSecret Scanningにブロックされたことがある
（`git reset --soft` で履歴を巻き戻して解決済み）。

---

## 完成している機能

### 1. 複数通貨ペアの監視（watch_list）

Settingsで、監視したい通貨ペアを個別に「時間軸（秒）」つきで追加・削除できる。
例:
- USD/JPY・20秒後
- EUR/USD・30秒後

それぞれ独立したTradingViewウィンドウ/タブを同時に開いておく前提。
ウィンドウタイトルに含まれる通貨ペア名（例: "USDJPY"）で自動検出する。

### 2. AI予想（High/Low）

`analyzer.py` がGemini APIにチャート画像を送り、以下を予想する。

- `direction`: "HIGH" または "LOW"（指定した秒数後の値動き）
- `confidence`: 0〜100の確信度
- `reason`: 判断理由
- `price`: 画面に表示されている現在価格（読み取れれば）

**重要な限界**: 数十秒程度の短期予想は、静止画のチャートから高精度で
当てられるようなものではない。実際の的中率は「勝率」表示で確認すること。

### 3. 自動判定（勝率の自動集計）

予想時に読み取った価格と、`horizon_seconds`経過後に再度読み取った価格を比較し、
自動でWIN/LOSS/UNKNOWNを判定する（`logger.py`の`resolve_outcome()`）。

**注意**: チャートに現在価格がはっきり数字で表示されていないと、
価格が読み取れずUNKNOWNになりやすい。

### 4. LINE通知

LINE Messaging API（Broadcast方式）で通知する。ユーザーID不要、
チャネルアクセストークンだけで送信できる。

無料枠（月200通）を節約するため、以下の両方を満たす時だけ通知する。

1. Settingsの「最低Confidence」以上の予想である
2. 前回そのペアで通知した方向（High/Low）から変わった（同方向が続く間は再通知しない）

### 5. 定期監視（QThread）

`monitor.py` が、有効な通貨ペアを順番に処理し続ける。GUIをブロックしない。

- 連続でAPIエラー（レート制限など）が起きた通貨ペアは、自動的に一時休止する
  （3回連続エラーで30秒→60秒→...最大5分の休止。他のペアの監視には影響しない）

### 6. 資金管理・成績集計（scoring.py）

- 口座残高×リスク許容率から「推奨ベット額」を計算し、LINE通知にも表示
- 通貨ペア別の勝率集計も可能（`calculate_win_rate_by_currency`）

---

## 使っているAIモデルについて（要・定期確認）

Gemini APIのモデルラインナップと無料枠は**頻繁に変わる**。
2026年7月時点では `gemini-3.1-flash-lite` を使っている
（`gemini-2.5-flash`系は新規ユーザー向けに廃止済み）。

404エラーや429（レート制限）エラーが出た場合は、Google公式ドキュメント
（https://ai.google.dev/gemini-api/docs/models）で最新のモデル名・無料枠を確認し、
`config.json`の`ai_model`とSettingsの選択肢を更新すること。

---

## 今後の課題・アイデア（優先度低〜未着手）

- **履歴閲覧画面**: `history.json`に溜まった過去の予想一覧をGUI上で見る画面
- **バックテスト・統計機能**: 過去データから、時間帯別・通貨ペア別の的中傾向を分析
- **デスクトップアプリ化**: PyInstallerなどで`.exe`化し、Python環境が無くても実行できるようにする
- **TradingViewウィンドウ検出の精度向上**: 現状はウィンドウタイトルの部分一致のみ

---

## 開発方針

「途中だけ修正するのではなく、ファイル単位の完成版で開発する」方針を継続。
毎回、変更したファイルは全文を渡し、可能な範囲で単体テストしてから共有する。
