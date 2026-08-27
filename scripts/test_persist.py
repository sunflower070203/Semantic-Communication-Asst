#!/usr/bin/env python3
"""Strict persistence test: send Q1, wait, close browser, then verify externally."""

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
        len0 = len(pg.evaluate("document.body.innerText || ''"))
        pg.locator("textarea[placeholder*='输入你的问题']").fill(Q1)
        pg.locator("button[class*='ChatInput--submit']").first.click()
        started = time.time()
        last = len0
        stable = 0
        while time.time() - started < 300:
            time.sleep(12)
            cur = len(pg.evaluate("document.body.innerText || ''"))
            if cur - len0 > 400 and cur == last:
                stable += 1
                if stable >= 3:
                    break
            else:
                stable = 0
            last = cur
        txt = pg.evaluate("document.body.innerText || ''")
        print("answered:", time.time() - started, "Q1_in_body:", "语义通信" in txt and "区别" in txt)
        print("body_len:", len(txt))
        # extra settle time so the share session commits
        print("settling 15s...")
        time.sleep(15)
        ctx.close()
        b.close()
    print("ctx closed. now open the share link in the REAL browser and check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
