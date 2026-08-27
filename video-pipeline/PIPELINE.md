# 荒れ判定AI競馬ラボ｜動画制作パイプライン v3

Keeneland / 札幌 / 新潟 の実績を踏まえ、視聴フィードバックを反映した版。

## 確定仕様（v3）

| 項目 | 内容 |
|------|------|
| 声 | `ja-JP-KeitaNeural`（男性） |
| 字幕 | **フレーズ単位TTSの実尺**でASS同期 |
| 画像 | 目標 **100枚** + **構図・時間帯・距離感の強制バリエーション** |
| 動き | **静止画＋短いクロスフェード**（Ken Burns / zoompan はデフォルトOFF） |
| 映像 | 1280×720 / H.264 Main / yuv420p |
| 音声 | AAC 44.1kHz ステレオ + `faststart` |
| リポジトリMP4 | **100MB未満** |

## v3 で変えた理由

1. **画像が似る** → 馬名一致だけでは同じ構図が繰り返されるため、カット番号で「寄り/引き/俯瞰/逆光/雨後」などを強制ローテーション
2. **ズーム・パンがガクガク** → ffmpeg `zoompan` は低解像度補間でジャギーが出やすい。視聴を邪魔するため、**静止画＋クロスフェード**に変更

## 工程（台本到着後）

1. 完成台本を `script/narration.txt` に貼る
2. `python3 video-pipeline/prepare_from_script.py --project <race-dir>`
3. `prompts/image_prompts.json` に沿って画像100枚生成 → `assets/scene_XXX.png`
4. `bash video-pipeline/build_video.sh <race-dir> <ass-basename> [output]`
5. PC確認 → commit / push / PR

## 動きモード（任意）

```bash
# デフォルト（推奨）: 静止画 + クロスフェード
MOTION=still_xfade bash video-pipeline/build_video.sh <race-dir> <ass>

# 旧方式（非推奨・検証用）
MOTION=kenburns bash video-pipeline/build_video.sh <race-dir> <ass>
```

`config.json` でも `"motion": "still_xfade"` を指定可。

## 画像プロンプトの多様性ルール

各カットは次を必ず変える:

- **距離**: extreme close-up / medium / wide / aerial-ish
- **アングル**: eye-level / low / high / side / over-shoulder
- **光**: morning / overcast / golden hour / blue hour / backlight
- **天候・空気**: clear / humid haze / after-rain wet turf / windy
- **被写体の役割**: track only / horse alone / paddock / crowd-bokeh / analysis desk / tickets

馬ごとの固定プロンプトがあっても、上記バリエーション層を必ず末尾に足す。

## ディレクトリ規約

```
<race-dir>/
  script/narration.txt
  config.json               # horses / motion / course_keywords
  prompts/image_prompts.json
  assets/scene_XXX.png
  audio/...
  subs/<name>.ass
  out/<output>.mp4
```

## 注意

- モバイルのチャット内再生は不安定なことがある → PC確認
- エンタメ／制作用。馬券は自己責任
