#!/usr/bin/env python3
"""Prefill 4 questions, close the browser, then report (verify share externally)."""

import json
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from record_demo_auto import SHARE_URL, prefill  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COOKIE_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".opentrek_cookies.json")


def main():
    with open(COOKIE_JSON, encoding="utf-8") as f:
        cookies = json.load(f)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_cookies(cookies)
        pg = ctx.new_page()
        pg.goto(SHARE_URL, timeout=60000, wait_until="domcontentloaded")
        prefill(pg)
        pg.close()
        ctx.close()
        b.close()
    print("prefill done, browser closed. verify via real browser now.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
