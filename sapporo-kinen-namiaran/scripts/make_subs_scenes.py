#!/usr/bin/env python3
"""Build ASS subtitles + timed scene list for Sapporo Kinen mid-upset video."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DUR = float((ROOT / "audio/duration.txt").read_text().strip())
TEXT = (ROOT / "script/narration.txt").read_text().strip()

# Narrative beat markers -> scene image (order matters; first match window)
# Markers must match FIRST intended occurrence (avoid early teaser lines).
BEATS = [
    ("競馬ラボです", "scene_01.png"),
    ("今年の札幌記念が、荒れるレースなのか", "scene_03.png"),
    ("AIスコアと過去10年のデータから", "scene_02.png"),
    ("最初に、今回の結論です", "scene_04.png"),
    ("という中波乱です", "scene_05.png"),
    ("見分けるポイントを、3つ確認します", "scene_05.png"),
    ("1つ目は、1番人気の成績です", "scene_06.png"),
    ("2つ目は、前走の格です", "scene_07.png"),
    ("3つ目は、人気と実績のズレです", "scene_08.png"),
    ("想定1番人気のアドマイヤテラ", "scene_09.png"),
    ("想定2番人気のショウヘイ", "scene_10.png"),
    ("想定3番人気のシェイクユアハート", "scene_11.png"),
    ("想定4番人気のローシャムパーク。この馬が、今回の本命です", "scene_12.png"),
    ("想定5番人気のサクラファレル", "scene_13.png"),
    ("ここまでを整理します", "scene_15.png"),
    ("1000円で買う場合の暫定プランです", "scene_14.png"),
    ("皆さんは、今年の札幌記念を", "scene_16.png"),
    ("最後までご覧いただき、ありがとうございました", "scene_17.png"),
]


def split_cues(text: str) -> list[str]:
    # Keep short mobile-friendly cues
    raw = re.split(r"(?<=[。！？])\s*", text.replace("\n", ""))
    cues: list[str] = []
    for s in raw:
        s = s.strip()
        if not s:
            continue
        if len(s) <= 28:
            cues.append(s)
            continue
        # soft split on 、
        parts = s.split("、")
        buf = ""
        for i, p in enumerate(parts):
            piece = p if i == len(parts) - 1 else p + "、"
            if buf and len(buf) + len(piece) > 28:
                cues.append(buf)
                buf = piece
            else:
                buf += piece
        if buf:
            cues.append(buf)
    return cues


def ts(sec: float) -> str:
    if sec < 0:
        sec = 0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def main() -> None:
    cues = split_cues(TEXT)
    weights = [max(len(c), 8) for c in cues]
    total_w = sum(weights)
    times = []
    t = 0.0
    for w in weights:
        dt = DUR * (w / total_w)
        times.append((t, t + dt))
        t += dt
    # snap last end to DUR
    times[-1] = (times[-1][0], DUR)

    # ASS
    ass = [
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
    for cue, (a, b) in zip(cues, times):
        # slight pad so cues don't flash
        end = min(DUR, max(a + 0.8, b))
        ass.append(f"Dialogue: 0,{ts(a)},{ts(end)},Default,,0,0,0,,{cue}")
    (ROOT / "subs/namiaran.ass").write_text("\n".join(ass) + "\n", encoding="utf-8")

    # Scene timeline from beats using first occurrence char index -> time
    flat = TEXT.replace("\n", "")
    scene_starts: list[tuple[float, str]] = []
    for marker, img in BEATS:
        idx = flat.find(marker.replace("\n", ""))
        if idx < 0:
            # try shortened
            idx = flat.find(marker[:8])
        if idx < 0:
            continue
        # map char index to time via cue cumulative weights
        # approximate: proportion of chars
        frac = idx / max(len(flat), 1)
        scene_starts.append((frac * DUR, img))

    # ensure start at 0 with first scene
    if not scene_starts or scene_starts[0][1] != "scene_01.png":
        scene_starts.insert(0, (0.0, "scene_01.png"))
    else:
        scene_starts[0] = (0.0, scene_starts[0][1])

    # dedupe consecutive same images; keep earliest
    cleaned: list[tuple[float, str]] = []
    for st, img in sorted(scene_starts, key=lambda x: x[0]):
        if cleaned and cleaned[-1][1] == img:
            continue
        # keep distinct beats even if close (hook needs fast cuts)
        if cleaned and st - cleaned[-1][0] < 2.5:
            # replace previous if nearly same time
            cleaned[-1] = (cleaned[-1][0], img)
            continue
        cleaned.append((st, img))

    # build segments until DUR
    segments = []
    for i, (st, img) in enumerate(cleaned):
        end = cleaned[i + 1][0] if i + 1 < len(cleaned) else DUR
        if end - st < 1.0:
            continue
        segments.append({"start": round(st, 3), "end": round(end, 3), "image": img, "dur": round(end - st, 3)})

    # if last ends early, extend
    if segments:
        segments[-1]["end"] = round(DUR, 3)
        segments[-1]["dur"] = round(DUR - segments[-1]["start"], 3)

    (ROOT / "scripts/scenes.json").write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")
    print("cues", len(cues), "scenes", len(segments), "dur", DUR)
    for s in segments:
        print(f"{s['start']:7.1f}-{s['end']:7.1f}  {s['dur']:6.1f}s  {s['image']}")


if __name__ == "__main__":
    main()
