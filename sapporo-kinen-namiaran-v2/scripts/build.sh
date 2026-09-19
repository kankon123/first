#!/usr/bin/env bash
# v2 build: phrase-synced subs, 100 scenes, varied Ken Burns + fades, 720p HQ
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
DUR=$(cat audio/duration.txt)
FPS=30
TMP=out/clips
mkdir -p "$TMP"

python3 <<'PY'
import json, subprocess, math
from pathlib import Path

ROOT = Path('.')
timeline = json.loads((ROOT/'audio/phrase_timeline.json').read_text())
fps = 30
tmp = ROOT/'out/clips'
tmp.mkdir(parents=True, exist_ok=True)

# Motion presets: (zoom_end, x_expr_template, y_expr_template)
# x/y use iw, ih, zoom, on, frames
MOTIONS = [
    (1.10, "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),  # center in
    (1.08, "(iw-iw/zoom)*on/{frames}", "ih/2-(ih/zoom/2)"),  # pan L->R
    (1.08, "(iw-iw/zoom)*(1-on/{frames})", "ih/2-(ih/zoom/2)"),  # pan R->L
    (1.09, "iw/2-(iw/zoom/2)", "(ih-ih/zoom)*on/{frames}"),  # pan top->bottom
    (1.09, "iw/2-(iw/zoom/2)", "(ih-ih/zoom)*(1-on/{frames})"),  # pan bottom->top
    (1.04, "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),  # gentle (almost hold)
    (1.12, "iw/2-(iw/zoom/2)+(iw*0.02)*sin(on/25)", "ih/2-(ih/zoom/2)"),  # soft drift
    (0.92, "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),  # zoom out (via start>end handled below)
]

list_lines = []
for item in timeline:
    i = item['i']
    secs = float(item['dur'])
    # tiny pad so visual covers audio phrase fully
    secs = max(secs, 0.8)
    frames = max(int(round(secs * fps)), 1)
    img = ROOT/'assets'/f'scene_{i:03d}.png'
    if not img.exists():
        raise SystemExit(f'missing {img}')
    out = tmp/f'c{i:03d}.mp4'
    zoom_end, x_t, y_t = MOTIONS[i % len(MOTIONS)]
    # For zoom-out presets (<1), invert: start high end 1.0
    if zoom_end < 1.0:
        z_expr = f"{1.0/zoom_end}-({1.0/zoom_end}-1)*on/{frames}"
    else:
        # ease-in-out-ish via smoothstep on
        z_expr = f"1+({zoom_end}-1)*(3*(on/{frames})^2-2*(on/{frames})^3)"
    x_expr = x_t.format(frames=frames)
    y_expr = y_t.format(frames=frames)
    fade = min(0.25, secs/4)
    vf = (
        f"scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s=1280x720:fps={fps},"
        f"fade=t=in:st=0:d={fade:.3f},fade=t=out:st={max(secs-fade,0):.3f}:d={fade:.3f},format=yuv420p"
    )
    cmd = [
        'ffmpeg','-y','-loop','1','-i',str(img),
        '-vf', vf,
        '-t', f'{secs:.3f}',
        '-c:v','libx264','-profile:v','main','-level','3.1','-pix_fmt','yuv420p',
        '-preset','fast','-crf','20','-an', str(out)
    ]
    print('clip', i, f'{secs:.2f}s', flush=True)
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    list_lines.append(f"file '{out.resolve()}'")

(tmp/'list.txt').write_text('\n'.join(list_lines)+'\n')
print('clips', len(list_lines))
PY

ffmpeg -y -f concat -safe 0 -i "$TMP/list.txt" -c copy "$TMP/video_silent.mp4"

ASS_ESC=$(python3 -c "import pathlib; print(pathlib.Path('subs/namiaran_v2.ass').resolve().as_posix().replace(':','\\\\:'))")
VDUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$TMP/video_silent.mp4")
# use min of audio/video
python3 - <<PY
import subprocess
from pathlib import Path
adur=float(Path('audio/duration.txt').read_text())
vdur=float("$VDUR")
print('audio', adur, 'video', vdur)
Path('audio/mux_dur.txt').write_text(str(min(adur, vdur)))
PY
MUX=$(cat audio/mux_dur.txt)

ffmpeg -y -i "$TMP/video_silent.mp4" -i audio/narration.mp3 \
  -filter_complex "[0:v]ass=${ASS_ESC}[v];[1:a]aresample=44100,aformat=channel_layouts=stereo,volume=2.0,apad=whole_dur=${MUX}[a]" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -profile:v main -level 3.1 -pix_fmt yuv420p -preset slow -crf 18 \
  -c:a aac -b:a 192k -ar 44100 -ac 2 \
  -t "$MUX" -movflags +faststart \
  out/sapporo_kinen_namiaran_v2.mp4

ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height,sample_rate,channels,profile -of default out/sapporo_kinen_namiaran_v2.mp4
ls -lh out/sapporo_kinen_namiaran_v2.mp4
