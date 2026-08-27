# 新潟記念2026｜動画制作準備

キーンランドC / 札幌記念v2 の工程を引き継いだ**制作枠**です。台本が来次第、すぐ本番に入れます。

## レース概要（準備時点）

| 項目 | 内容 |
|------|------|
| レース | 第62回 新潟記念（G3） |
| 日時 | 2026-08-30（日） 15:45 |
| コース | 新潟 芝2000m（外） |
| 条件 | 3歳以上オープン・別定 |

※出走馬・枠順・斤量は台本作成時点の情報で上書きすること。

## 引き継いだ仕様（変更なし）

- 声: **Keita**
- 字幕: フレーズ単位TTS実尺同期
- 画像: **100枚**
- 動き: パン/ズーム多様化＋フェード
- 出力: 720p / 44.1kHzステレオAAC / faststart / **100MB未満**

詳細: `../video-pipeline/PIPELINE.md`

## いまの状態

| 項目 | 状態 |
|------|------|
| 共通パイプライン | ✅ `video-pipeline/` |
| プロジェクト枠 | ✅ `niigata-kinen-2026/` |
| 馬名テーマ設定 | ✅ `config.json`（台本に合わせて追記可） |
| 完成台本 | ⏳ **待ち** → `script/narration.txt` |
| TTS / 画像 / 本編 | ⏳ 台本到着後 |

## 台本が来たらやること

1. 読み上げ本文を `script/narration.txt` に保存（見出しや注釈は除く）
2. 必要なら `config.json` の `horses` に登場馬を追加
3. 準備コマンド:

```bash
export PATH="$HOME/.local/bin:$PATH"
pip3 install edge-tts -q
python3 video-pipeline/prepare_from_script.py \
  --project niigata-kinen-2026 \
  --ass-name niigata
```

4. `prompts/image_prompts.json` に沿って画像100枚 → `assets/scene_000.png`〜
5. ビルド:

```bash
bash video-pipeline/build_video.sh niigata-kinen-2026 niigata niigata_kinen_2026
```

6. PCで確認 → commit / push / PR

## 依頼時に欲しいもの

- 完成台本（読み上げ全文）
- 想定人気・オッズ基準日（台本に書いてあればOK）
- （任意）サムネ文言 / YouTubeタイトル

台本を貼ってもらえれば、この枠で動画化に入ります。
