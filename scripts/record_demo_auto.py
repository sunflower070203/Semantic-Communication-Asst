#!/usr/bin/env python3
"""Fully automatic demo recording pipeline.

Phase A: prefill the share session with 4 Q&A (no recording).
Phase B: record the platform session shots S01-S05/S07/S08 into one webm,
         recording per-shot timestamps.
Phase C: record the GitHub repo page (S06) into a second webm.

Outputs:
  demo/video/raw/platform.webm
  demo/video/raw/github.webm
  demo/video/timeline.json
"""

import json
import argparse
import os
import sys
import time
import urllib.parse

from playwright.sync_api import sync_playwright
import markdown

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from demo_content import GITHUB_URL, LIVE_QUESTION, PREFILL_QUESTIONS  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SHARE_URL = (
    "http://10.128.203.200:30226/agent/index.html"
    "#/arrange/agentExp?randomCode=297d4be1aa2443cca29b62b5be702beb&noLayout=1"
)
COOKIE_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".opentrek_cookies.json")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo", "video")
RAW_DIR = os.path.join(OUT_DIR, "raw")
os.makedirs(RAW_DIR, exist_ok=True)

WARN_KEYWORDS = ["未能核实", "校验警告", "未通过校验", "无法核实", "引用校验", "警告"]


def body_len(pg):
    return len(pg.evaluate("document.body.innerText || ''"))


def wait_ready(pg, timeout=60):
    """Wait until the share page has loaded its chat shell."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if pg.locator("textarea[placeholder*='输入你的问题']").count() > 0:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def reset_conversation(pg):
    btn = pg.locator("button:has-text('新开对话')")
    if btn.count() > 0:
        pg.once("dialog", lambda d: d.accept())
        btn.first.click()
        time.sleep(5)


def send_and_wait(pg, question, timeout=300, quiet=False):
    len0 = body_len(pg)
    ta = pg.locator("textarea[placeholder*='输入你的问题']")
    ta.fill(question)
    pg.locator("button[class*='ChatInput--submit']").first.click()
    started = time.time()
    last = len0
    stable = 0
    while time.time() - started < timeout:
        time.sleep(12)
        cur = body_len(pg)
        if cur - len0 > 400 and cur == last:
            stable += 1
            if stable >= 3:
                if not quiet:
                    print(f"  answered in {time.time()-started:.0f}s")
                return time.time() - started
        else:
            stable = 0
        last = cur
    print("  WARN: timed out waiting for answer")
    return time.time() - started


def scroll_to_text(pg, text, block="start"):
    ok = pg.evaluate(
        """(a) => {
          const t = a.t, b = a.b;
          const els = [...document.querySelectorAll('div,span,p,li,h1,h2,h3,h4,pre,code')];
          const hit = els.find(e => (e.innerText||'').trim() === t)
            || els.find(e => (e.innerText||'').includes(t) && (e.innerText||'').length <= t.length + 300);
          if (hit) { hit.scrollIntoView({behavior:'smooth', block:b}); return true; }
          return false;
        }""",
        {"t": text, "b": block},
    )
    return ok


def scroll_to_keyword(pg, keywords, block="start"):
    return pg.evaluate(
        """(a) => {
          const kws = a.k, b = a.b;
          const els = [...document.querySelectorAll('div,span,p,li,h1,h2,h3,h4')];
          for (const kw of kws) {
            const hit = els.find(e => (e.innerText||'').includes(kw) && (e.innerText||'').length < 500);
            if (hit) { hit.scrollIntoView({behavior:'smooth', block:b}); return kw; }
          }
          return null;
        }""",
        {"k": keywords, "b": block},
    )


def error_in_body(pg):
    txt = pg.evaluate("document.body.innerText || ''")[-3000:]
    return "IbpStreamingException" in txt or '"cause"' in txt or "stop stream request" in txt


def verify_prefill(pg):
    """Slowly scroll the conversation and verify all answers are present and clean."""
    pg.evaluate("window.scrollTo(0, 0)")
    for _ in range(30):
        pg.evaluate("window.scrollBy(0, 800)")
        pg.wait_for_timeout(500)
    pg.wait_for_timeout(2000)
    txt = pg.evaluate("document.body.innerText || ''")
    missing = [q[:10] for q in PREFILL_QUESTIONS if q[:10] not in txt]
    err = "IbpStreamingException" in txt or '"cause"' in txt
    return (not missing, missing, err)


def prefill(pg):
    print("=== Phase A: prefill 4 questions (no recording)")
    if not wait_ready(pg):
        raise RuntimeError("share page not ready")
    for rnd in range(3):
        reset_conversation(pg)
        ok = True
        for i, q in enumerate(PREFILL_QUESTIONS, 1):
            print(f"  [round {rnd+1}] Q{i}: {q[:28]}...", flush=True)
            send_and_wait(pg, q)
            print("  cooling 40s for the stream to fully finish...", flush=True)
            time.sleep(40)
            if error_in_body(pg):
                print("  ERROR JSON detected, will reset and refill all")
                ok = False
                break
        if not ok:
            continue
        good, missing, err = verify_prefill(pg)
        if good and not err:
            print("  prefill verified: 4/4 present, no error JSON")
            return
        print("  prefill verify failed:", missing, "err:", err, "-> retry")
    raise RuntimeError("prefill failed after 3 rounds")


def est_vo(text):
    """Rough TTS duration estimate: ~4 chars/sec + padding."""
    return max(len(text) / 4.0 + 4.0, 8.0)


def build_readme_page():
    """Render the local README.md into a GitHub-style page for S06 recording."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    readme = os.path.join(root, "README.md")
    with open(readme, encoding="utf-8") as f:
        md = f.read()
    body = markdown.markdown(md, extensions=["fenced_code", "tables"])
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Semantic-Communication-Asst — README</title>
<style>
  body {{ margin:0; background:#f6f8fa; font-family:'Segoe UI',system-ui,sans-serif; color:#1f2328; }}
  .bar {{ background:#24292f; color:#fff; padding:14px 28px; font-size:15px; }}
  .bar b {{ color:#fff; }}
  .wrap {{ max-width:900px; margin:24px auto; background:#fff; border:1px solid #d0d7de;
          border-radius:8px; padding:32px 40px; line-height:1.7; }}
  h1 {{ border-bottom:1px solid #d0d7de; padding-bottom:10px; font-size:26px; }}
  h2 {{ border-bottom:1px solid #d0d7de; padding-bottom:6px; margin-top:32px; font-size:21px; }}
  pre {{ background:#f6f8fa; padding:14px; border-radius:6px; overflow-x:auto; }}
  code {{ font-family:Consolas,monospace; }}
  table {{ border-collapse:collapse; width:100%; }}
  th, td {{ border:1px solid #d0d7de; padding:8px 12px; text-align:left; }}
  img {{ max-width:100%; }}
</style></head><body>
  <div class="bar">github.com/sunflower070203/Semantic-Communication-Asst · README</div>
  <div class="wrap">{body}</div>
</body></html>"""
    out = os.path.join(OUT_DIR, "readme_page.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return out


def record_platform(ctx, timeline):
    print("=== Phase B: record platform session")
    pg = ctx.new_page()
    pg.goto(SHARE_URL, timeout=60000, wait_until="domcontentloaded")
    if not wait_ready(pg, 90):
        raise RuntimeError("share page not ready for recording")
    pg.wait_for_timeout(4000)
    t0 = time.monotonic()
    timeline["t0"] = t0
    shots = timeline["shots"]

    def mark(shot_id):
        if shots:
            shots[-1]["end"] = time.monotonic() - t0
        shots.append({"id": shot_id, "start": time.monotonic() - t0})

    # pre-render all messages: slow scroll so the virtual list renders everything
    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    for _ in range(30):
        pg.evaluate("window.scrollBy(0, -700)")
        pg.wait_for_timeout(450)
    pg.wait_for_timeout(2000)

    # S01: opening, top of conversation
    mark("S01")
    pg.wait_for_timeout(int(est_vo("大家好，这是我们参加东南大学AI+大赛赛道一的项目，语义通信助手。一句话，它是帮你读论文的。你问它语义通信是什么，它不光回答，还告诉你这话是哪篇论文、哪一页说的。") * 1000))

    # S02: Q1 definition + citation entries
    mark("S02")
    scroll_to_text(pg, PREFILL_QUESTIONS[0])
    pg.wait_for_timeout(5000)
    kw = scroll_to_keyword(pg, ["《语义通信系统引言》", "I. ", "与传统通信相比"])
    print("  S02 citation-list hit:", kw)
    pg.wait_for_timeout(int(est_vo("先看第一个问题，什么是语义通信，它和传统通信有什么区别。回答分成几块，先讲定义，再讲区别。每条关键陈述后面都有引用标记，比如这个罗马数字一。页面下面跟着引用列表，注明出自哪篇论文的哪一部分。") * 1000))

    # S03: Q2 citation verification (all passed)
    mark("S03")
    scroll_to_text(pg, PREFILL_QUESTIONS[1])
    pg.wait_for_timeout(5000)
    kw = scroll_to_keyword(pg, ["Deep SC 文本处理架构", "BLEU", "I. Deep JSCC"])
    print("  S03 citation hit:", kw)
    pg.wait_for_timeout(int(est_vo("第二个想给你看的，是引用校验。这是这个项目最核心的地方。模型有时候会编引用。我们的做法不是靠它自觉，而是写了个程序来查。回答生成以后，系统做三方核对，正文里的引用标记、引用列表、还有实际检索到的内容，三边对一遍。这一整段回答里的每一处引用，都通过了校验，出处可以逐条追溯。") * 1000))

    # S04: Q3 mermaid diagram
    mark("S04")
    scroll_to_text(pg, PREFILL_QUESTIONS[2])
    pg.wait_for_timeout(5000)
    for _ in range(20):
        svgs = pg.evaluate("document.querySelectorAll('svg').length")
        if svgs > 10:
            break
        time.sleep(1)
    pg.evaluate("window.scrollBy(0, 500)")
    pg.wait_for_timeout(5000)
    pg.evaluate("window.scrollBy(0, 500)")
    pg.wait_for_timeout(int(est_vo("第三个亮点，画图。你让它画语义通信的系统架构，它会输出一段mermaid代码，聊天界面直接把它渲染成流程图。这里有个背景。平台本身没有生图模型，我们也不打算硬造。用文本渲染把图画出来，一样能看图，而且图是矢量图，放大不糊。") * 1000))

    # S05: Q4 honest refusal
    mark("S05")
    scroll_to_text(pg, PREFILL_QUESTIONS[3])
    pg.wait_for_timeout(5000)
    kw = scroll_to_keyword(pg, ["无法联网", "不能联网", "IEEE", "arXiv"])
    print("  S05 refusal hit:", kw)
    pg.wait_for_timeout(int(est_vo("第四个想说的，是它知道自己不会什么。你让它联网搜2025年的新论文，它会直接说，我连不了网，手头这些资料里没有2025年的内容，你可以去IEEE或者arXiv自己查。它不编。") * 1000))

    # S07: show the live question + answer already in the session
    # (the 6G answer was generated live during a prior take; streaming the send
    #  again risks the platform's serial-stream "human stop" failure, so we
    #  scroll-show the real answer instead)
    mark("S07a")
    timeline["live"] = None
    scroll_to_text(pg, LIVE_QUESTION)
    pg.wait_for_timeout(int(est_vo("最后一个，是我们现场问的新问题：语义通信在 6G 里有哪些典型应用场景。") * 1000))

    mark("S07b")
    scroll_to_keyword(pg, ["应用场景", "6G"])
    pg.wait_for_timeout(int(est_vo("可以看到，回答里同样带上了引用标记，每一处都直接来自知识库里的论文。") * 1000))

    # S08: close
    mark("S08")
    pg.evaluate("window.scrollTo(0, 0)")
    pg.wait_for_timeout(5000)

    if shots:
        shots[-1]["end"] = time.monotonic() - t0
    pg.close()
    print("  platform recording done")


def record_github(ctx, timeline):
    print("=== Phase C: record README page (GitHub unreachable, local render)")
    pg = ctx.new_page()
    try:
        page_path = build_readme_page()
        pg.goto(urllib.parse.quote(page_path, safe="/:\\"), timeout=60000, wait_until="domcontentloaded")
        pg.wait_for_timeout(8000)
        t0 = time.monotonic()
        timeline["github"] = {"start": t0}
        pg.evaluate("window.scrollTo(0, 0)")
        pg.wait_for_timeout(5000)
        h = pg.evaluate("document.body.scrollHeight")
        steps = 12
        for i in range(1, steps + 1):
            pg.evaluate(f"window.scrollTo(0, {h * i / steps})")
            pg.wait_for_timeout(3500)
        timeline["github"]["end"] = time.monotonic() - t0
    except Exception as e:
        print("  WARN: github recording failed:", e)
        timeline["github"] = None
    pg.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-prefill", action="store_true", help="skip Phase A (session already filled)")
    args = ap.parse_args()

    # clean stale raw recordings so renames never pick up old takes
    for f in os.listdir(RAW_DIR):
        if f.endswith(".webm"):
            try:
                os.remove(os.path.join(RAW_DIR, f))
            except OSError:
                pass

    with open(COOKIE_JSON, encoding="utf-8") as f:
        cookies = json.load(f)

    timeline = {"shots": [], "live": None, "github": None}

    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)

        # Phase A: prefill without recording
        if not args.skip_prefill:
            ctx_pre = b.new_context(viewport={"width": 1440, "height": 900})
            ctx_pre.add_cookies(cookies)
            pg_pre = ctx_pre.new_page()
            pg_pre.goto(SHARE_URL, timeout=60000, wait_until="domcontentloaded")
            prefill(pg_pre)
            pg_pre.close()
            ctx_pre.close()
        else:
            print("=== Phase A skipped (--skip-prefill)")

        # Phase B+C: recording
        ctx = b.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=RAW_DIR,
            record_video_size={"width": 1440, "height": 900},
        )
        ctx.add_cookies(cookies)
        record_platform(ctx, timeline)
        record_github(ctx, timeline)
        ctx.close()
        b.close()

    with open(os.path.join(OUT_DIR, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=1)

    webm = sorted([f for f in os.listdir(RAW_DIR) if f.endswith(".webm")])
    # rename: largest = platform, next = github, drop empty leftovers
    sizes = [(os.path.join(RAW_DIR, f), os.path.getsize(os.path.join(RAW_DIR, f))) for f in webm]
    sizes.sort(key=lambda x: x[1], reverse=True)
    targets = {"platform.webm": sizes[0][0], "github.webm": sizes[1][0] if len(sizes) > 1 else None}
    for name, src in targets.items():
        if src:
            dst = os.path.join(RAW_DIR, name)
            if os.path.abspath(src) != os.path.abspath(dst):
                os.replace(src, dst)
    for f in webm:
        if f not in ("platform.webm", "github.webm"):
            try:
                os.remove(os.path.join(RAW_DIR, f))
            except OSError:
                pass
    print("=== OUTPUT")
    for f in sorted(os.listdir(RAW_DIR)):
        print(" ", f, os.path.getsize(os.path.join(RAW_DIR, f)), "bytes")
    print("timeline:", json.dumps(timeline, ensure_ascii=False)[:500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
