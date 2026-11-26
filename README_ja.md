# ExamRAG

[![tests](https://github.com/huiren789/exam-rag/actions/workflows/tests.yml/badge.svg)](https://github.com/huiren789/exam-rag/actions/workflows/tests.yml)
![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)
![MIT](https://img.shields.io/badge/license-MIT-green)
[![Live demo](https://img.shields.io/badge/demo-live-green)](https://examrag-demo.app.workbuddy.host/?sharecode=YTW7YFIS3R)

<div align="center">

<img src="assets/demo.png" alt="ExamRAG デモ：質問・検索・出典" width="880">

**根拠まで辿れる、試験勉強のパートナー**

**依存ゼロ · 出典つき · 教材は差し替え自由** — 検索はローカルで行い、選んだ資料だけを LLM に渡します。回答には必ず出典が付き、原文に戻って確認できます。

[オンラインデモ（API キー不要）](https://examrag-demo.app.workbuddy.host/?sharecode=YTW7YFIS3R) ·
[解決する問題](#解決する問題) ·
[30 秒で自分の科目に切り替える](#30-秒で自分の科目に切り替える)

</div>

**言語**：[中文](README.md) · [English](README_en.md) · **日本語** · [한국어](README_ko.md) · [Español](README_es.md)

> 同梱の「教育 measurement」教材はサンプルです。`data/material.txt` を差し替えれば**どの科目にも使えます**。検索のコアは Python 標準ライブラリのみ。作者本人が第一ユーザーとして実際の勉強に使い、自作の評価セットで 4 回改良しました。

## 解決する問題

いきなり LLM に聞くと、もっともらしいのに捏造された回答が返ることがあります。教科書を自分で読むと、欲しい一節を探すのが大変です。

ExamRAG は「資料を探す」手順をローカルで行います。検索はオフライン・無料・結果が見えます。選んだ資料ブロックだけをモデルに送り、その資料だけを使う・出典を書く・資料になければ「記載なし」と答えるようプロンプトで強制します。

## 30 秒で自分の科目に切り替える

同梱教材は例です。自分のノートを次の形式のプレーンテキストに整えるだけです：

```text
【掌握·概念名】概念を一段で説明する本文。
【理解·別の概念】……
【了解·三つ目の概念】……
```

3 つのラベル（掌握 / 理解 / 了解）が出題時の重み付けを決めます。あとは：

```bash
python -m examrag -q "あなたの質問" --material my.txt
```

または `EXAMRAG_MATERIAL=my.txt` を一度設定すればOK。検索・出典・重み付き出題・Web UI はそのまま動きます。**特定の科目専用のツールとの決定的な違いです**。

## 主な機能

- ローカル語彙検索（bigram 頻度、タイトル加重、目次・要約は減点）— 標準ライブラリのみ
- 任意の TF-IDF 意味検索（`--semantic`）— オフライン・依存なし
- 任意の embedding ベクトル検索（`--vector`）— キャッシュ付き
- 文単位の根拠表示 — Web UI で出典句から原文へジャンプ
- 重み付き出題（掌握 ×3 / 理解 ×2 / 了解 ×1）
- クエリ書き換え・重难点まとめ・並列概念の分割検索
- オフライン dry-run（`--dry-run`）— キーなしで検索結果とプロンプトを表示
- Web UI と FastAPI（5 エンドポイント、Swagger 自動生成）
- 89 件のオフラインテスト、CI（Python 3.8 / 3.11 / 3.13 + ruff）

## クイックスタート

```bash
git clone https://github.com/huiren789/exam-rag.git
cd exam-rag
python -m examrag -q "難度とは" --dry-run   # オフライン・キー不要
python -m examrag                             # 対話モード
```

実際にモデルを呼ぶ場合は `.env.example` を `.env` にコピーして `SILICONFLOW_API_KEY` を設定。Web UI は WorkBuddy Cloud 経由なので[デモ](https://examrag-demo.app.workbuddy.host/?sharecode=YTW7YFIS3R)はキー不要です。

## 制限事項

- 既定は語彙検索。TF-IDF は言い回しの差を吸収し、同義語レベルの回想には embedding が必要。
- 根拠句は中文の句読点ヒューリスティック。非常に長い文や複数文にまたがる表現は精度が落ちます。
- 教材は手動整形が必要（PDF / Word 取り込みは未対応）。
- 会話の文脈は保持しません。各質問が独立に検索します。

## ドキュメント

[中文完全版](README.md) · [English](README_en.md) · [設計判断](docs/adr) · [変更履歴](CHANGELOG.md)

## ライセンス

[MIT](LICENSE) © 2026 huiren789
