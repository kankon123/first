#!/usr/bin/env python3
"""Prepare phrase-synced TTS, ASS, and image prompts from narration.txt."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
from collections import Counter
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


def theme_for(text: str, i: int, horses: dict[str, str], course_hint: str) -> str:
    for name, prompt in horses.items():
        if name in text:
            return prompt
    if any(k in text for k in ("馬単", "3連単", "高配当", "ワイド", "馬券", "1000円")):
        return "close-up racing tickets with soft turf bokeh, warm decision mood, no readable numbers, photoreal, no logos"
    if any(k in text for k in ("結論", "判定", "診断", "まとめ", "AI")):
        return "dark teal cinematic racing analysis desk with subtle glowing nodes, no readable text, no logos"
    if any(k in text for k in ("消", "危険", "切り")):
        return "lonely thoroughbred walking away from grandstand under cloudy sky, photoreal, no text no logos"
    if course_hint and any(k in text for k in course_hint.split("|")):
        return "Japanese turf racecourse wide establishing shot, long straight, cool daylight, photoreal, no text no logos"
    if any(k in text for k in ("コメント", "質問", "皆さんは")):
        return "empty racecourse grandstand at blue hour, contemplative mood, photoreal, no text no logos"
    if any(k in text for k in ("LINE", "概要欄", "枠順")):
        return "quiet turf rail at dusk with soft fog, calm closing mood, photoreal, no text no logos"
    generics = [
        "wide Japanese turf track curve under soft overcast, white rail, photoreal, no text no logos",
        "jockey and thoroughbred walking to paddock, shallow depth, photoreal, no text no logos",
        "finish-line perspective on green turf with distant trees, photoreal, no text no logos",
        "racehorses warming up on turf track, soft haze, photoreal, no text no logos",
        "grandstand silhouette against cloudy sky, photoreal, no text no logos",
        "single thoroughbred cantering past camera on turf, photoreal, no text no logos",
        "starting gate atmosphere empty before race, tense calm, photoreal, no text no logos",
        "analytical notebook and stopwatch near turf window light, no readable text, photoreal",
    ]
    return generics[i % len(generics)]


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
                "prompt": f"{base}, 16:9 composition, edge-to-edge, variation {i+1}, high detail",
            }
        )
    prompts_dir = project / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "image_prompts.json").write_text(
        json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    theme_count = len(
        Counter(theme_for(c, i, horses, course_hint).split(",")[0][:24] for i, c in enumerate(cues))
    )
    print("prompts", len(prompts), "themes", theme_count)
    print("done", project)


if __name__ == "__main__":
    main()
