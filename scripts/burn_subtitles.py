#!/usr/bin/env python3
"""Burn per-shot captions into the final video as ASS subtitles."""

import os
import subprocess
import sys

import imageio_ffmpeg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from demo_content import SHOTS  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VIDEO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo", "video")
SRC = os.path.join(VIDEO, "semantic-comms-demo.mp4")
OUT = os.path.join(VIDEO, "semantic-comms-demo_subbed.mp4")

# shot order in the final film (mirrors compose_video.py)
SHOT_ORDER = ["S01", "S02", "S03", "S04", "S05", "S06", "S07a", "S07b", "S08"]

# measured durations from the last compose run (seconds)
DUR = {
    "S01": 24.2, "S02": 32.8, "S03": 43.0, "S04": 41.8, "S05": 30.8,
    "S06": 50.0, "S07a": 13.0, "S07b": 12.5, "S08": 5.0,
}


def ass_escape(text):
    return text.replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")


def ts(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int((sec - int(sec)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def main():
    by_id = {s["id"]: s for s in SHOTS}
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1440
PlayResY: 900
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Microsoft YaHei,46,&H00FFFFFF,&H000000FF,&H00101010,&H96000000,-1,0,0,0,100,100,0,0,1,3,1,2,80,80,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    t = 0.0
    for sid in SHOT_ORDER:
        shot = by_id[sid]
        cap = shot.get("caption") or ""
        if cap:
            start = t + 1.0
            end = t + DUR[sid] - 1.0
            if end > start + 1.0:
                events.append(
                    f"Dialogue: 0,{ts(start)},{ts(end)},Cap,,0,0,0,,{ass_escape(cap)}"
                )
        t += DUR[sid]

    ass_path = os.path.join(VIDEO, "captions.ass")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
    print("ASS written:", ass_path, len(events), "events")

    r = subprocess.run(
        [
            FFMPEG, "-y", "-i", SRC,
            "-vf", "ass=captions.ass",
            "-c:v", "libx264", "-crf", "20", "-preset", "medium",
            "-c:a", "copy", OUT,
        ],
        cwd=VIDEO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        print(r.stderr[-1500:])
        return 1
    print("burned:", OUT, os.path.getsize(OUT), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
