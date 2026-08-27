#!/usr/bin/env python3
"""Smoke test: Playwright + injected cookies opens the logged-in share session."""

import json
import os
import sys

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SHARE_URL = (
    "http://10.128.203.200:30226/agent/index.html"
    "#/arrange/agentExp?randomCode=297d4be1aa2443cca29b62b5be702beb&noLayout=1"
)
COOKIE_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".opentrek_cookies.json")


def main():
    with open(COOKIE_JSON, encoding="utf-8") as f:
        cookies = json.load(f)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_cookies(cookies)
        pg = ctx.new_page()
        pg.goto(SHARE_URL, timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(8000)
        print("FINAL_URL:", pg.url)
        if "/login" in pg.url:
            print("LOGIN REDIRECT: cookies did not work")
            pg.screenshot(path="smoke_login.png")
            b.close()
            return 1
        txt = pg.evaluate("document.body.innerText || ''")
        print("BODY_LEN:", len(txt))
        print("TEXT_HEAD:", txt[:400].replace("\n", " | "))
        pg.screenshot(path="smoke_share.png")
        b.close()
    print("SHARE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
