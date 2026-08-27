#!/usr/bin/env python3
"""Compose the final demo video from raw recordings.

1. Generate TTS voice-over per shot (edge-tts).
2. Cut platform.webm into per-shot clips using timeline.json.
3. Speed up the live-question waiting segment (S07).
4. Mux each clip with its VO, concat in order, write semantic-comms-demo.mp4.
"""

import asyncio
import json
import os
import subprocess
import sys
import time

import edge_tts
import imageio_ffmpeg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from demo_content import SHOTS, TTS_VOICE  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO = os.path.join(ROOT, "demo", "video")
RAW = os.path.join(VIDEO, "raw")
WORK = os.path.join(VIDEO, "work")
os.makedirs(WORK, exist_ok=True)

CRF = 20
WAIT_SPEEDUP = 15.0


def run(args):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {args}\n{r.stderr[-1500:]}")
    return r


def dur(path):
    r = run([FFMPEG, "-i", path, "-f", "null", "-"])
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            h, m, s = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError("no duration found for " + path)


def gen_vo():
    out = {}
    vo_dir = os.path.join(WORK, "vo")
    os.makedirs(vo_dir, exist_ok=True)

    def one(shot):
        path = os.path.join(vo_dir, f"{shot['id']}.mp3")
        if os.path.exists(path):
            os.remove(path)  # always regenerate: stale partial files are untrustworthy
        expect = max(len(shot["vo"]) / 4.0, 4.0)
        for attempt in range(4):
            try:
                asyncio.run(edge_tts.Communicate(shot["vo"], TTS_VOICE).save(path))
            except Exception as e:
                print(f"  VO {shot['id']} attempt {attempt+1} failed: {e}")
                time.sleep(2)
                continue
            d = dur(path)
            if d >= expect * 0.5:
                break
            print(f"  VO {shot['id']} too short ({d:.1f}s < {expect*0.5:.1f}s), retrying")
        out[shot["id"]] = {"path": path, "dur": dur(path)}
        if out[shot["id"]]["dur"] < expect * 0.5:
            raise RuntimeError(f"VO generation failed for {shot['id']}")
        print(f"  VO {shot['id']}: {out[shot['id']]['dur']:.1f}s")

    for s in SHOTS:
        one(s)
    return out


def cut(inp, out, start, length):
    run([FFMPEG, "-y", "-ss", f"{start:.2f}", "-i", inp, "-t", f"{length:.2f}", "-c:v", "libx264", "-crf", str(CRF), "-preset", "medium", out])


def speedup(inp, out, factor):
    run([FFMPEG, "-y", "-i", inp, "-filter:v", f"setpts={1/factor}*PTS", "-an", "-c:v", "libx264", "-crf", str(CRF), "-preset", "medium", out])


def mux(clip, vo, out, total):
    if vo:
        run([FFMPEG, "-y", "-i", clip, "-i", vo, "-filter_complex", "[1:a]apad[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}", out])
    else:
        run([FFMPEG, "-y", "-i", clip, "-c:v", "copy", "-an", out])


def concat(clips, out):
    lst = os.path.join(WORK, "list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{c.replace(os.sep, '/')}'\n")
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])


def build_shot_clips(timeline, vo):
    platform = os.path.join(RAW, "platform.webm")
    github = os.path.join(RAW, "github.webm")
    shots = timeline["shots"]
    live = timeline.get("live")
    by_id = {s["id"]: s for s in shots}
    clips = []

    for shot in SHOTS:
        sid = shot["id"]
        if sid == "S06":
            if timeline.get("github"):
                src = github
                st, en = 0.0, 50.0
                clip = os.path.join(WORK, "clip_S06.mp4")
                cut(src, clip, st, min(en, dur(src)))
                clips.append({"id": sid, "clip": clip, "vo": vo.get(sid), "dur": min(en, dur(src))})
            else:
                print("  WARN: no github recording, S06 skipped")
            continue
        if (sid == "S07a" or sid == "S07b") and live is not None:
            continue  # handled below
        rec = by_id[sid]
        st = rec["start"]
        ln = rec["end"] - rec["start"]
        clip = os.path.join(WORK, f"clip_{sid}.mp4")
        cut(platform, clip, st, ln)
        vdur = vo.get(sid, {}).get("dur", 0)
        total = max(ln, vdur + 1.0)
        fin = os.path.join(WORK, f"fin_{sid}.mp4")
        mux(clip, vo.get(sid, {}).get("path"), fin, total)
        clips.append({"id": sid, "clip": fin, "dur": total})
        print(f"  shot {sid}: rec={ln:.1f}s vo={vdur:.1f}s -> {total:.1f}s")

    # S07: send segment + sped-up wait + answer segment
    if live:
        send = live["send"]
        ans = live.get("answer")
        seg_send = os.path.join(WORK, "s07_send.mp4")
        seg_wait_src = os.path.join(WORK, "s07_wait_src.mp4")
        seg_wait = os.path.join(WORK, "s07_wait.mp4")
        seg_ans = os.path.join(WORK, "s07_ans.mp4")
        cut(platform, seg_send, max(0.0, send - 5.0), 7.0)
        if ans:
            cut(platform, seg_wait_src, send + 2.0, max(0.0, ans - (send + 2.0)))
            cut(platform, seg_ans, ans, 11.0)
        else:
            seg_wait_src = None
            seg_ans = None
        if seg_wait_src and os.path.getsize(seg_wait_src) > 4096:
            speedup(seg_wait_src, seg_wait, WAIT_SPEEDUP)
        elif seg_wait_src:
            seg_wait = seg_wait_src
        d_send = dur(seg_send)
        vo_a = vo.get("S07a", {}).get("path")
        fin_a = os.path.join(WORK, "fin_S07a.mp4")
        mux(seg_send, vo_a, fin_a, max(d_send, vo.get("S07a", {}).get("dur", 0) + 0.5))
        clips.append({"id": "S07a", "clip": fin_a, "dur": dur(fin_a)})
        if seg_wait_src:
            d_wait = dur(seg_wait)
            clips.append({"id": "S07wait", "clip": seg_wait, "dur": d_wait})
        if seg_ans:
            d_ans = dur(seg_ans)
            vo_b = vo.get("S07b", {}).get("path")
            fin_b = os.path.join(WORK, "fin_S07b.mp4")
            mux(seg_ans, vo_b, fin_b, max(d_ans, vo.get("S07b", {}).get("dur", 0) + 0.5))
            clips.append({"id": "S07b", "clip": fin_b, "dur": dur(fin_b)})
            print(f"  shot S07: send={d_send:.1f}s wait={d_wait:.1f}s ans={d_ans:.1f}s")
        else:
            print("  shot S07: send only (no live answer recorded)")
    else:
        print("  note: no live-send segment; S07 shown from pre-filled session")

    return clips


def main():
    with open(os.path.join(VIDEO, "timeline.json"), encoding="utf-8") as f:
        timeline = json.load(f)
    print("=== TTS voice-over")
    vo = gen_vo()
    print("=== cutting + muxing shots")
    clips = build_shot_clips(timeline, vo)
    final = os.path.join(VIDEO, "semantic-comms-demo.mp4")
    concat([c["clip"] for c in clips], final)
    print("=== DONE")
    print("final:", final, os.path.getsize(final), "bytes,", f"{dur(final):.1f}s")
    for c in clips:
        print(" ", c["id"], f"{c['dur']:.1f}s")


if __name__ == "__main__":
    main()
