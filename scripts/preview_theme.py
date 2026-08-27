#!/usr/bin/env python3
"""Preview: current share-page look vs. injected premium dark theme."""

import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SHARE_URL = (
    "http://10.128.203.200:30226/agent/index.html"
    "#/arrange/agentExp?randomCode=297d4be1aa2443cca29b62b5be702beb&noLayout=1"
)
COOKIE_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".opentrek_cookies.json")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo", "video")

PREMIUM_CSS = """
:root { color-scheme: dark; }
html { background: #0a0e1a !important; }
body { background: linear-gradient(160deg, #0a0e1a 0%, #0d1226 55%, #101a33 100%) !important;
       color: #e6edf3 !important; font-family: 'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif !important; }
body, div, span, p, h1, h2, h3, h4, li, section { color: inherit; }

/* chat shell panels */
[class*="layout"], [class*="Layout"], [class*="panel"], [class*="Panel"],
[class*="container"], [class*="Container"], [class*="main"], [class*="Main"],
[class*="body"], [class*="Body"], [class*="wrapper"], [class*="Wrapper"] {
  background: transparent !important;
}

/* assistant answer cards */
[class*="answer"], [class*="Answer"], [class*="assistant"], [class*="Assistant"],
[class*="message"], [class*="Message"], [class*="chat"], [class*="Chat"],
[class*="content"], [class*="Content"], [class*="bubble"], [class*="Bubble"] {
  background: rgba(255,255,255,0.035) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 14px !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.35) !important;
}

/* user question bubbles: accent edge */
[class*="user"], [class*="User"], [class*="question"], [class*="Question"] {
  background: rgba(34, 211, 238, 0.10) !important;
  border: 1px solid rgba(34, 211, 238, 0.28) !important;
  border-radius: 14px !important;
}

/* citation markers */
[class*="citation"], [class*="Citation"], [class*="ref"], [class*="Ref"] {
  color: #22d3ee !important; font-weight: 600 !important;
}

/* headings & strong */
h1, h2, h3, h4, strong, b { color: #f1f5ff !important; }

/* input area */
textarea, [class*="input"], [class*="Input"] {
  background: #121830 !important; color: #e6edf3 !important;
  border: 1px solid #263255 !important; border-radius: 12px !important;
}
textarea::placeholder { color: #64748b !important; }
[class*="submit"], [class*="Submit"], button[class*="primary"] {
  background: linear-gradient(135deg, #22d3ee, #3b82f6) !important;
  color: #04121a !important; border-radius: 10px !important; border: none !important;
}

/* mermaid diagrams in dark */
svg { background: transparent !important; }
svg text { fill: #c9d4e8 !important; }
svg rect, svg path[id*="node"], svg .node rect { fill: #1b2440 !important; stroke: #3b82f6 !important; }
svg .edgePath path { stroke: #64748b !important; }
svg .edgeLabel { fill: #94a3b8 !important; }

/* topbar / misc chrome */
[class*="header"], [class*="Header"], [class*="topbar"], [class*="Topbar"],
[class*="nav"], [class*="Nav"] { background: rgba(10,14,26,0.85) !important; }

/* scrollbar */
::-webkit-scrollbar { width: 9px; height: 9px; }
::-webkit-scrollbar-thumb { background: #263255; border-radius: 8px; }
::-webkit-scrollbar-track { background: transparent; }
"""


def main():
    with open(COOKIE_JSON, encoding="utf-8") as f:
        cookies = json.load(f)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_cookies(cookies)
        pg = ctx.new_page()
        pg.goto(SHARE_URL, timeout=45000, wait_until="domcontentloaded")
        deadline = time.time() + 90
        while time.time() < deadline:
            if pg.locator("textarea[placeholder*='输入你的问题']").count() > 0:
                break
            time.sleep(2)
        pg.wait_for_timeout(3000)
        # scroll to the Q1 answer area so the preview shows real content
        pg.evaluate(
            """() => {
              const els = [...document.querySelectorAll('div')];
              const hit = els.find(e => (e.innerText||'').includes('语义通信是一种以准确提取'));
              if (hit) hit.scrollIntoView({block:'center'});
            }"""
        )
        pg.wait_for_timeout(1500)
        before = os.path.join(OUT, "preview_before.png")
        pg.screenshot(path=before)

        pg.add_style_tag(content=PREMIUM_CSS)
        pg.wait_for_timeout(1500)
        bg = pg.evaluate("getComputedStyle(document.body).backgroundImage.slice(0,60)")
        after = os.path.join(OUT, "preview_after.png")
        pg.screenshot(path=after)
        print("before:", before)
        print("after:", after)
        print("body bg:", bg)
        b.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
