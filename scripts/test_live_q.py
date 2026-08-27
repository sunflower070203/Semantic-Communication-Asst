#!/usr/bin/env python3
"""Test: does asking the live 6G question reset the share session?"""

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
LIVE_Q = "语义通信在6G里有哪些典型应用场景？"


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
        before = pg.evaluate("document.body.innerText || ''")
        print("BEFORE: len=", len(before), "has_Q1=", "语义通信" in before)
        len0 = len(before)
        ta = pg.locator("textarea[placeholder*='输入你的问题']")
        ta.fill(LIVE_Q)
        pg.locator("button[class*='ChatInput--submit']").first.click()
        print("sent live question")
        samples = []
        for i in range(12):
            time.sleep(10)
            cur = pg.evaluate("document.body.innerText || ''")
            samples.append(len(cur))
            welcome = "请问您需要了解哪方面的信息" in cur
            if i in (0, 3, 6, 9, 11):
                print(f"  t={(i+1)*10}s len={len(cur)} welcome={welcome}")
        after = pg.evaluate("document.body.innerText || ''")
        print("AFTER: len=", len(after), "has_live_q=", "6G" in after, "welcome=", "请问您需要了解哪方面的信息" in after)
        ctx.close()
        b.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
