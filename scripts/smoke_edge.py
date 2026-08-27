#!/usr/bin/env python3
"""Smoke test: drive system Edge via Playwright, open the OpenTrek platform."""

from playwright.sync_api import sync_playwright
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 1280, "height": 800})
        pg.goto(
            "http://10.128.203.200:30226/agent/index.html",
            timeout=45000,
            wait_until="domcontentloaded",
        )
        pg.wait_for_timeout(6000)
        print("FINAL_URL:", pg.url)
        print("TITLE:", pg.title())
        txt = pg.evaluate(
            "document.body ? document.body.innerText.slice(0,300) : 'no body'"
        )
        print("TEXT:", txt.replace("\n", " | ")[:300])
        pg.screenshot(path="smoke_platform.png")
        b.close()
    print("SMOKE OK")


if __name__ == "__main__":
    main()
