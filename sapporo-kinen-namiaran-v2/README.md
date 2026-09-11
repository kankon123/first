# 札幌記念2026｜中波乱AI判定 v2（改善版）

v1への改善対応版です。

## 改善内容

| 項目 | v1 | v2 |
|------|----|----|
| 字幕同期 | 文字数按分（ズレあり） | **フレーズ単位TTSの実尺で同期** |
| 画像枚数 | 17枚 | **100枚** |
| 動き | 中央ズームのみ | **8種のパン/ズーム＋フェード** |
| 画質 | CRF22 / preset fast | **CRF18 / preset slow**（720pのまま高画質化） |

## 仕様

- 尺: 約10分08秒
- 声: Keita（男性）
- 出力: `out/sapporo_kinen_namiaran_v2.mp4`
- 1280×720 / H.264 Main / AAC 44.1kHz stereo / faststart / ASS焼き込み

## 再ビルド

画像と `audio/phrase_timeline.json` / `subs/namiaran_v2.ass` / `audio/narration.mp3` がある状態で:

```bash
# フレーズ音声が無い場合は先にTTS再生成が必要
bash scripts/build.sh
```

## ファイルサイズ

GitHub制限のためリポジトリ内MP4は約97MB（CRF21）。より高画質なHQ版（CRF18・約137MB）はアーティファクト側に保存。

## 確認メモ

モバイルのチャット内再生が不安定なときは PC、または `audio/narration.mp3` 単体で確認。
