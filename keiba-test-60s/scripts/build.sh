#!/usr/bin/env bash
# Build ~53s Sapporo Kinen test video: 720p + Keita + burned-in ASS
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DUR=$(cat "$ROOT/audio/duration.txt")
# pad to even seconds for clip lengths
TOTAL=${DUR%.*}
# four scenes: roughly equal
SEG=$(python3 -c "print(round($DUR/4, 3))")
FPS=30
OUTDIR="$ROOT/out"
TMP="$OUTDIR/clips"
mkdir -p "$TMP"

mkclip() {
  local img="$1" out="$2" secs="$3" zoom_end="$4"
  # Ken Burns: slow zoom from 1.0 toward zoom_end
  local frames
  frames=$(python3 -c "print(int(round($secs * $FPS)))")
  ffmpeg -y -loop 1 -i "$img" -vf "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,zoompan=z='1+($zoom_end-1)*on/${frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=${frames}:s=1280x720:fps=${FPS},format=yuv420p" \
    -t "$secs" -c:v libx264 -profile:v main -level 3.1 -pix_fmt yuv420p -preset fast -crf 22 -an "$out"
}

mkclip "$ROOT/assets/scene_01.png" "$TMP/c1.mp4" "$SEG" 1.08
mkclip "$ROOT/assets/scene_02.png" "$TMP/c2.mp4" "$SEG" 1.10
mkclip "$ROOT/assets/scene_03.png" "$TMP/c3.mp4" "$SEG" 1.06
# last clip absorbs remainder so A/V stay in sync
LAST=$(python3 -c "print(round($DUR - 3*$SEG, 3))")
mkclip "$ROOT/assets/scene_04.png" "$TMP/c4.mp4" "$LAST" 1.05

printf "file '%s'\n" "$TMP/c1.mp4" "$TMP/c2.mp4" "$TMP/c3.mp4" "$TMP/c4.mp4" > "$TMP/list.txt"
ffmpeg -y -f concat -safe 0 -i "$TMP/list.txt" -c copy "$TMP/video_silent.mp4"

# burn ASS + mux AAC 44.1k stereo + faststart
ffmpeg -y -i "$TMP/video_silent.mp4" -i "$ROOT/audio/narration.mp3" \
  -filter_complex "[0:v]ass=${ROOT}/subs/sapporo.ass[v];[1:a]aresample=44100,aformat=channel_layouts=stereo,volume=2.2,apad=whole_dur=${DUR}[a]" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -profile:v main -level 3.1 -pix_fmt yuv420p -preset fast -crf 22 \
  -c:a aac -b:a 160k -ar 44100 -ac 2 \
  -t "$DUR" -movflags +faststart \
  "$OUTDIR/sapporo_kinen_60s.mp4"

ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height,sample_rate,channels,profile -of default "$OUTDIR/sapporo_kinen_60s.mp4"
ls -lh "$OUTDIR/sapporo_kinen_60s.mp4"
