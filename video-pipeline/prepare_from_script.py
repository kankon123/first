#!/usr/bin/env python3
"""Prepare phrase-synced TTS, ASS, and image prompts from narration.txt."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
from pathlib import Path

DEFAULT_VOICE = "ja-JP-KeitaNeural"
TARGET_CUES = 100


def split_cues(text: str, target: int = TARGET_CUES) -> list[str]:
    parts = re.split(r"(?<=[。！？])\s*", text.replace("\n", " "))
    sents = [p.strip() for p in parts if p.strip()]
    cues: list[str] = []
    for s in sents:
        if len(s) <= 36:
            cues.append(s)
            continue
        chunks = s.split("、")
        buf = ""
        for i, c in enumerate(chunks):
            piece = c if i == len(chunks) - 1 else c + "、"
            if buf and len(buf) + len(piece) > 36:
                cues.append(buf)
                buf = piece
            else:
                buf += piece
        if buf:
            cues.append(buf)

    while len(cues) > target:
        best = None
        for i in range(len(cues) - 1):
            L = len(cues[i]) + len(cues[i + 1])
            if best is None or L < best[0]:
                best = (L, i)
        i = best[1]
        cues[i] = cues[i] + cues[i + 1]
        del cues[i + 1]

    guard = 0
    while len(cues) < target:
        j = max(range(len(cues)), key=lambda k: len(cues[k]))
        s = cues[j]
        if "、" in s:
            a, b = s.split("、", 1)
            cues[j : j + 1] = [a + "、", b]
        elif len(s) > 18:
            mid = len(s) // 2
            cues[j : j + 1] = [s[:mid], s[mid:]]
        else:
            break
        guard += 1
        if guard > 300:
            break
    return cues


def ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def probe_dur(path: Path) -> float:
    return float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            text=True,
        ).strip()
    )


def load_config(project: Path) -> dict:
    cfg_path = project / "config.json"
    if cfg_path.exists():
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    return {}


# Forced visual variety so consecutive cuts do not look identical.
DISTANCES = [
    "extreme close-up detail",
    "tight portrait framing",
    "medium shot",
    "full-body shot",
    "wide establishing shot",
    "very wide landscape framing",
]
ANGLES = [
    "eye-level camera",
    "low-angle hero shot",
    "high-angle looking down",
    "side profile angle",
    "three-quarter angle",
    "over-the-rail viewpoint",
]
LIGHTS = [
    "soft morning light",
    "bright overcast daylight",
    "golden hour warm side light",
    "blue hour cool twilight",
    "strong backlight with rim light",
    "diffused cloudy stadium light",
]
ATMOSPHERES = [
    "clear crisp air",
    "humid summer haze",
    "after-rain wet turf sheen",
    "dusty paddock atmosphere",
    "wind-blown mane suggestion",
    "quiet empty-track stillness",
]
SUBJECTS = [
    "empty turf and white rail only",
    "single thoroughbred centered",
    "two horses overlapping in depth",
    "paddock walk scene",
    "crowd as soft bokeh only",
    "finish-line geometry focus",
    "analysis desk with papers and monitor glow",
    "betting tickets in shallow depth of field",
    "starting gate structure without readable text",
    "grandstand architecture silhouette",
]


def variety_suffix(i: int) -> str:
    d = DISTANCES[i % len(DISTANCES)]
    a = ANGLES[(i // 2) % len(ANGLES)]
    l = LIGHTS[(i // 3) % len(LIGHTS)]
    at = ATMOSPHERES[(i // 5) % len(ATMOSPHERES)]
    s = SUBJECTS[(i * 3) % len(SUBJECTS)]
    # Unique constraint line reduces near-duplicates across a 100-cut set.
    return (
        f"{d}, {a}, {l}, {at}, primary subject: {s}, "
        f"distinct composition #{i+1}, avoid repeating previous framing, "
        f"no text, no logos, no readable saddle cloths"
    )


def base_theme(text: str, i: int, horses: dict[str, str], course_hint: str) -> str:
    for name, prompt in horses.items():
        if name in text:
            return prompt
    if any(k in text for k in ("馬単", "3連単", "高配当", "ワイド", "馬券", "1000円")):
        return "Japanese racing tickets and soft turf bokeh, warm decision mood, no readable numbers, photoreal"
    if any(k in text for k in ("結論", "判定", "診断", "まとめ", "AI", "中波乱", "大荒れ")):
        return "cinematic racing analysis atmosphere with subtle data glow, dark teal charcoal palette, no readable text"
    if any(k in text for k in ("消", "危険", "切り", "様子見")):
        return "isolated thoroughbred mood of doubt, cooler color grade, photoreal"
    if any(k in text for k in ("ハンデ", "別定", "斤量", "条件")):
        return "symbolic weight-and-condition metaphor via empty saddle cloth area and rail geometry, no readable text, photoreal"
    if any(k in text for k in ("距離", "2000", "マイル", "1200", "芝")):
        return "distance emphasis on long turf corridor or short sprint chute, photoreal"
    if course_hint and any(k in text for k in course_hint.split("|")):
        return "Japanese turf racecourse establishing atmosphere matching the race venue, photoreal"
    if any(k in text for k in ("コメント", "質問", "皆さんは")):
        return "empty grandstand question-ending mood, contemplative, photoreal"
    if any(k in text for k in ("LINE", "概要欄", "枠順")):
        return "quiet closing atmosphere at the rail, soft fog, photoreal"
    generics = [
        "Japanese turf track geometry and rail lines, photoreal",
        "paddock tension before a graded race, photoreal",
        "finish-straight perspective with distant trees, photoreal",
        "warm-up gallop atmosphere on turf, photoreal",
        "architecture of a Japanese grandstand under cloud, photoreal",
        "single horse canter freeze with shallow depth, photoreal",
        "pre-race stillness near the gate area, photoreal",
        "desk-side research mood with turf visible through window, no readable text, photoreal",
        "wet grass texture macro after watering, photoreal",
        "shadow of a horse across the rail at dusk, photoreal",
    ]
    return generics[i % len(generics)]


def theme_for(text: str, i: int, horses: dict[str, str], course_hint: str) -> str:
    return f"{base_theme(text, i, horses, course_hint)}, {variety_suffix(i)}"

async def synth_all(cues: list[str], out_dir: Path, voice: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    import edge_tts

    sem = asyncio.Semaphore(4)

    async def run(i: int, t: str) -> None:
        async with sem:
            await edge_tts.Communicate(t, voice).save(str(out_dir / f"{i:03d}.mp3"))
            if i % 10 == 0:
                print("tts", i, flush=True)

    await asyncio.gather(*[run(i, t) for i, t in enumerate(cues)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="Race project directory")
    ap.add_argument("--ass-name", default="narration", help="ASS basename without extension")
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--skip-tts", action="store_true")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    narration = project / "script" / "narration.txt"
    if not narration.exists():
        raise SystemExit(f"missing {narration}")

    text = narration.read_text(encoding="utf-8").strip()
    if not text or text.startswith("（台本待ち"):
        raise SystemExit("narration.txt is empty or still a placeholder")

    cfg = load_config(project)
    horses = cfg.get("horses", {})
    course_hint = cfg.get("course_keywords", "新潟|芝2000|外回り")
    voice = cfg.get("voice", args.voice)
    ass_name = cfg.get("ass_name", args.ass_name)

    cues = split_cues(text)
    (project / "script").mkdir(parents=True, exist_ok=True)
    (project / "script" / "cues.json").write_text(
        json.dumps(cues, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("cues", len(cues), "chars", sum(len(c) for c in cues))

    phrases = project / "audio" / "phrases"
    if not args.skip_tts:
        asyncio.run(synth_all(cues, phrases, voice))

    times = []
    t = 0.0
    for i, cue in enumerate(cues):
        d = probe_dur(phrases / f"{i:03d}.mp3")
        times.append({"i": i, "start": t, "end": t + d, "dur": d, "text": cue})
        t += d

    audio = project / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    (audio / "phrase_timeline.json").write_text(
        json.dumps(times, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (audio / "duration.txt").write_text(str(t), encoding="utf-8")
    print("TOTAL", round(t, 2))

    lst = phrases / "list.txt"
    lst.write_text("".join(f"file '{i:03d}.mp3'\n" for i in range(len(cues))))
    raw = audio / "narration_raw.mp3"
    final = audio / "narration.mp3"
    subprocess.check_call(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(raw)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.check_call(
        ["ffmpeg", "-y", "-i", str(raw), "-ar", "44100", "-ac", "2", "-b:a", "160k", str(final)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1280",
        "PlayResY: 720",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Droid Sans Fallback,36,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,3,1,2,40,40,48,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for item in times:
        ass_lines.append(
            f"Dialogue: 0,{ts(item['start'])},{ts(item['end'])},Default,,0,0,0,,{item['text']}"
        )
    subs = project / "subs"
    subs.mkdir(parents=True, exist_ok=True)
    (subs / f"{ass_name}.ass").write_text("\n".join(ass_lines) + "\n", encoding="utf-8")

    prompts = []
    for i, cue in enumerate(cues):
        base = theme_for(cue, i, horses, course_hint)
        prompts.append(
            {
                "i": i,
                "cue": cue,
                "prompt": (
                    f"{base}, 16:9 widescreen, edge-to-edge frame, photoreal racing documentary still, "
                    f"high detail, unique shot id {i+1:03d}"
                ),
            }
        )
    prompts_dir = project / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "image_prompts.json").write_text(
        json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Count unique variety combos (distance+angle+light roughly)
    variety_keys = [
        f"{DISTANCES[i % len(DISTANCES)]}|{ANGLES[(i // 2) % len(ANGLES)]}|{LIGHTS[(i // 3) % len(LIGHTS)]}"
        for i in range(len(cues))
    ]
    print("prompts", len(prompts), "variety_combos", len(set(variety_keys)))
    print("done", project)


if __name__ == "__main__":
    main()
