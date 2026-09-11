# 次回制作からの改善メモ（v3）

視聴フィードバックをパイプラインに反映済み。

## 1. 画像が似る → バリエーション強制

`prepare_from_script.py` が各カットに必ず付与:

- 距離（寄り〜超引き）
- アングル（アイレベル / ロー / ハイ 等）
- 光（朝 / 曇 / 逆光 / ブルーアワー 等）
- 空気感（晴 / 霞 / 雨後 等）
- 被写体役割（馬単体 / パドック / チケット / 空コース 等）

馬名プロンプトがあっても、上記レイヤーは毎回変える。

## 2. ズーム・パンがガクガク → デフォルト静止画

`build_video.sh` のデフォルトを **`still_xfade`** に変更。

- 動きなしの静止画
- 短いフェードイン/アウトのみ（切替を柔らかく）
- 旧 Ken Burns は `MOTION=kenburns` のときだけ（非推奨）

## 3. 読み上げ速度 → デフォルト 1.1 倍

`prepare_from_script.py` が TTS 後に **atempo=1.1** をかけ、フレーズ尺・ASS も同じ比率で縮める。

- 標準: 何も指定しなければ 1.1
- 例外: `--speed 1.0` または `config.json` の `"speed": 1.0`
- 過去に公開済みのレース動画は再エンコードしない（新規から適用）

## 次回の制作時

台本が来たら、いつもどおり:

```bash
python3 video-pipeline/prepare_from_script.py --project <race-dir>
# 画像生成（新しい多様な prompts を使用）
bash video-pipeline/build_video.sh <race-dir> <ass-name>
```

追加作業は不要。このブランチの `video-pipeline/` を使えば自動で v3 + 1.1倍になる。
