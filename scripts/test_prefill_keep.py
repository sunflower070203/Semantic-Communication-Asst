#!/usr/bin/env python3
"""Test: send Q1 via Playwright, wait for answer, reopen share, verify persistence."""

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
Q1 = "什么是语义通信？它和传统通信有什么区别？"


def body_len(pg):
    return len(pg.evaluate("document.body.innerText || ''"))


def send_and_wait(pg, question, timeout=300):
    len0 = body_len(pg)
    ta = pg.locator("textarea[placeholder*='输入你的问题']")
    ta.fill(question)
    pg.locator("button[class*='ChatInput--submit']").first.click()
    started = time.time()
    last = len0
    stable = 0
    while time.time() - started < timeout:
        time.sleep(15)
        cur = body_len(pg)
        if cur - len0 > 400 and cur == last:
            stable += 1
            if stable >= 3:
                return time.time() - started
        else:
            stable = 0
        last = cur
    return time.time() - started


def main():
    with open(COOKIE_JSON, encoding="utf-8") as f:
        cookies = json.load(f)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        # recording enabled from the start: we will re-open the page for the real take
        ctx = b.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir="demo/video_test",
            record_video_size={"width": 1440, "height": 900},
        )
        ctx.add_cookies(cookies)

        pg = ctx.new_page()
        pg.goto(SHARE_URL, timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(6000)
        el = send_and_wait(pg, Q1)
        print(f"Q1 answered in {el:.0f}s, body_len={body_len(pg)}")
        pg.close()

        pg2 = ctx.new_page()
        pg2.goto(SHARE_URL, timeout=45000, wait_until="domcontentloaded")
        pg2.wait_for_timeout(6000)
        txt = pg2.evaluate("document.body.innerText || ''")
        print(f"reopen body_len={len(txt)}, Q1 visible={'语义通信' in txt and '区别' in txt}")
        pg2.close()

        videos = []
        for root, _, files in os.walk("demo/video_test"):
            for f in files:
                fp = os.path.join(root, f)
                videos.append((fp, os.path.getsize(fp)))
        print("videos:", videos)
        b.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
