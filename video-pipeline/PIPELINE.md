# 荒れ判定AI競馬ラボ｜動画制作パイプライン（継承版）

キーンランドC / 札幌記念 v2 で確定した工程を、レース横断で再利用する。

## 確定仕様

| 項目 | 内容 |
|------|------|
| 声 | `ja-JP-KeitaNeural`（男性） |
| 字幕 | **フレーズ単位TTSの実尺**でASS同期 |
| 画像 | 目標 **100枚**（1カット約6〜12秒） |
| 動き | 8種パン/ズーム＋フェードイン/アウト |
| 映像 | 1280×720 / H.264 Main / yuv420p |
| 音声 | AAC 44.1kHz ステレオ + `faststart` |
| リポジトリMP4 | **100MB未満**（必要ならCRFを上げて再圧縮） |

## 工程（台本到着後）

1. 完成台本を `script/narration.txt` に貼る（読み上げ本文のみ）
2. `python3 video-pipeline/prepare_from_script.py --project <race-dir>`
   - cues分割（〜100）
   - Keita TTS（フレーズ単位）
   - `audio/narration.mp3` / `phrase_timeline.json`
   - `subs/<name>.ass`
   - `prompts/image_prompts.json`
3. 画像100枚を生成 → `assets/scene_000.png` … `scene_099.png`
4. `bash video-pipeline/build_video.sh <race-dir> <ass-basename>`
5. 100MB超なら自動で再圧縮、または手動でCRF上げ
6. commit / push / PR（PC再生で確認）

## ディレクトリ規約

```
<race-dir>/
  script/narration.txt      # 必須・読み上げ本文
  script/full_script.md     # 任意・元台本コピー
  script/cues.json          # prepare が生成
  audio/narration.mp3
  audio/phrase_timeline.json
  audio/duration.txt
  prompts/image_prompts.json
  assets/scene_XXX.png      # 000-099
  subs/<name>.ass
  out/<output>.mp4
  config.json               # 馬名・テーマ上書き（任意）
```

## 参照実績

- `sapporo-kinen-namiaran-v2/` … 字幕同期＋100枚＋動き改善の原型
- `keeneland-cup-2026/`（別ブランチ）… 同工程で本番1本

## 注意

- モバイルのチャット内再生は不安定なことがある → PC確認
- エンタメ／制作用。馬券は自己責任
