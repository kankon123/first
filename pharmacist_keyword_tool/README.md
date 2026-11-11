# 薬剤師副業キーワード調査ツール

薬剤師向けYouTubeチャンネル「薬剤師の副業ミライ地図」の初期動画企画のために、  
**視聴者が実際に検索している複合キーワード**を収集・整理する小規模ツールです。

メインキーワード: `薬剤師 副業`

## できること

- Google検索サジェストの取得（公開オートコンプリートAPI）
- YouTube検索サジェストの取得（同上）
- ラッコキーワード等のCSV取り込み
- GoogleキーワードプランナーCSVの取り込みと、既存キーワードへのボリューム照合
- 重複削除・表記ゆれ整理・検索意図カテゴリ分類
- 次のファイル出力
  - `keywords_raw.csv` … 取得元データの記録
  - `keywords_clean.csv` … 整理・分類後
  - `keywords_priority.csv` … 企画評価用（ボリューム未取得は「評価保留」）
  - `report.md` … 日本語の調査サマリー

## できないこと・やらないこと

- 利用規約に抵触しうるHTMLスクレイピング、CAPTCHA回避、アクセス制限の迂回
- 検索ボリュームの推測・捏造
- データが取れなかった場合の架空キーワード埋め
- 外部サービスへの自動ログインや有料API契約の代行
- YouTube競合動画の再生数分析（今回スコープ外）

## 必要な環境

- Windows 10/11（macOS / Linux でも動作確認可能な構成）
- Python 3.10 以上推奨（3.12 で確認）

## インストール

```bat
cd pharmacist_keyword_tool
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

macOS / Linux の場合:

```bash
cd pharmacist_keyword_tool
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 必要なライブラリ

| ライブラリ | 用途 |
|---|---|
| `requests` | Google / YouTube サジェストAPIへのHTTPリクエスト |
| `PyYAML` | `config.yaml` の読み込み |

標準ライブラリ（`csv`, `argparse`, `json`, `logging` など）のみでも処理の大半は動作しますが、上記2つは必須です。

## 実行方法

プロジェクトフォルダで:

```bat
python run.py
```

オプション:

```bat
REM サジェスト取得を飛ばし、CSVだけ処理
python run.py --skip-suggest

REM 既存の keywords_raw.csv を読み直し、整理とレポートだけ再生成
python run.py --reprocess-raw

REM 出力先を指定
python run.py --output-dir data\output
```

再実行しても同じ手順で上書き出力されます（再現可能）。

## 入力CSVの置き方

`data/input/` に次のような名前で置くと自動取り込みします。

| 想定ソース | ファイル名の例 | 必須列の例 |
|---|---|---|
| ラッコキーワード | `rakko_keywords.csv` | `キーワード` / 任意で `月間検索数` |
| キーワードプランナー | `planner_export.csv` | `キーワード` または `Keyword` / 任意で `平均月間検索ボリューム` や `Avg. monthly searches` |

入力CSVが無くても異常終了しません。サジェスト結果だけで出力します。

サンプル形式は `data/samples/` を参照してください（中身は形式説明用で、調査結果には使いません）。

### 人間側で必要な操作（有料・ログイン系）

1. **ラッコキーワード**  
   ブラウザでログインし、「薬剤師 副業」関連のCSVをエクスポート → `data/input/rakko_*.csv` に保存。
2. **Googleキーワードプランナー**  
   Google広告アカウントでキーワードプランナーを開き、関連語をエクスポート → `data/input/planner_*.csv` に保存。
3. 再度 `python run.py` を実行すると、既存キーワードとボリュームが照合されます。

※ 本ツールはこれらのサービスへログインしません。

## 出力ファイル

すべて `data/output/` に出力されます。

- `keywords_raw.csv` … UTF-8 BOM（Excel向け）
- `keywords_clean.csv`
- `keywords_priority.csv`
- `report.md`
- `errors.log` / `errors.csv` … 取得失敗の記録
- `run_summary.json` … 実行サマリー

### 重要な区別

- **実データ**: APIやCSVから実際に取得したもの（`is_example_data=no`）
- **例示データ**: READMEや指示書に書いた説明用の例。結果CSVには混ぜません
- **サジェストに存在する**ことと、**月間検索数が多い**ことは別です
- 検索ボリューム未取得時は順位を付けず **評価保留** とします

## カテゴリ（検索意図）

- 副業の種類・おすすめ
- 単発勤務・ダブルワーク
- 在宅勤務
- 収入・時給
- 税金・確定申告
- 法律・就業規則
- スキル活用・個人事業
- その他

ルールは `config.yaml` の `categories` で変更できます。

## 今回の実測メモ（参考）

- Googleサジェストからは関連複合語を安定して取得できました。
- YouTubeサジェストは、同じシードでも「薬剤師」「副業」の両方を含む候補が少ないことがあります（取得0件に近い場合あり）。これは欠損をごまかさず、そのまま記録します。
- 検索ボリュームはCSV投入がない限りすべて「未確認」です。

## トラブルシュート

- サジェストが0件 / エラーが多い場合: ネットワーク、DNS、ファイアウォールを確認。`data/output/errors.log` を見てください。403が続く場合は間隔を空けて再実行してください。
- Excelで文字化けする場合: 出力は UTF-8 BOM です。それでも壊れる場合は Excel の「データ」→「テキストファイル」から UTF-8 指定で開いてください。
- CSVが読み込まれない場合: 1行目にキーワード列名があるか確認してください。

## ディレクトリ構成

```text
pharmacist_keyword_tool/
  README.md
  requirements.txt
  config.yaml
  run.py
  src/
    main.py
    collectors.py
    csv_importer.py
    process.py
    report.py
    utils.py
  data/
    input/          # ユーザーがCSVを置く場所
    samples/        # 形式サンプル（調査結果には未使用）
    output/         # 実行結果
```
