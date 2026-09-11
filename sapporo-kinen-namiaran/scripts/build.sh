#!/usr/bin/env bash
# Build ~10min mid-upset Sapporo Kinen video: 720p + Keita + burned-in ASS
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 scripts/make_subs_scenes.py

DUR=$(cat audio/duration.txt)
FPS=30
TMP=out/clips
mkdir -p "$TMP"

python3 <<'PY'
import json, subprocess, math
from pathlib import Path
ROOT = Path('.')
segs = json.loads((ROOT/'scripts/scenes.json').read_text())
fps = 30
tmp = ROOT/'out/clips'
tmp.mkdir(parents=True, exist_ok=True)
list_path = tmp/'list.txt'
lines = []
for i, s in enumerate(segs):
    img = ROOT/'assets'/s['image']
    out = tmp/f'c{i:02d}.mp4'
    secs = float(s['dur'])
    frames = max(int(round(secs * fps)), 1)
    zoom_end = 1.06 + (i % 3) * 0.02
    # Ken Burns
    vf = (
        f"scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        f"zoompan=z='1+({zoom_end}-1)*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1280x720:fps={fps},format=yuv420p"
    )
    cmd = [
        'ffmpeg','-y','-loop','1','-i',str(img),
        '-vf', vf,
        '-t', f'{secs:.3f}',
        '-c:v','libx264','-profile:v','main','-level','3.1','-pix_fmt','yuv420p',
        '-preset','veryfast','-crf','23','-an', str(out)
    ]
    print('clip', i, s['image'], secs)
    subprocess.check_call(cmd)
    lines.append(f"file '{out.resolve()}'")
list_path.write_text('\n'.join(lines)+'\n')
print('wrote', list_path)
PY

ffmpeg -y -f concat -safe 0 -i "$TMP/list.txt" -c copy "$TMP/video_silent.mp4"

# burn ASS + mux AAC 44.1k stereo + faststart
# escape ASS path for filter
ASS_ESC=$(python3 -c "import pathlib; print(pathlib.Path('subs/namiaran.ass').resolve().as_posix().replace(':','\\\\:'))")

ffmpeg -y -i "$TMP/video_silent.mp4" -i audio/narration.mp3 \
  -filter_complex "[0:v]ass=${ASS_ESC}[v];[1:a]aresample=44100,aformat=channel_layouts=stereo,volume=2.0,apad=whole_dur=${DUR}[a]" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -profile:v main -level 3.1 -pix_fmt yuv420p -preset fast -crf 22 \
  -c:a aac -b:a 160k -ar 44100 -ac 2 \
  -t "$DUR" -movflags +faststart \
  out/sapporo_kinen_namiaran.mp4

ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height,sample_rate,channels,profile -of default out/sapporo_kinen_namiaran.mp4
ls -lh out/sapporo_kinen_namiaran.mp4
