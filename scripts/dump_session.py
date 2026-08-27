#!/usr/bin/env python3
"""Dump the share session text to a file for keyword inspection."""

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
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo", "session_dump.txt")


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
        # slow scroll to force render
        pg.evaluate("window.scrollTo(0, 0)")
        for _ in range(40):
            pg.evaluate("window.scrollBy(0, 700)")
            pg.wait_for_timeout(400)
        pg.wait_for_timeout(2000)
        txt = pg.evaluate("document.body.innerText || ''")
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(txt)
        print("dumped", len(txt), "chars ->", OUT)
        b.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
