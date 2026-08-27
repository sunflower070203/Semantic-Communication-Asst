#!/usr/bin/env python3
"""Dump the share-session message list to verify Q1-Q5 content."""

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
CHECKS = [
    "什么是语义通信",
    "Deep JSCC 和 DeepSC",
    "架构流程图",
    "联网搜索2025",
    "6G",
    "引用列表",
    "无法联网",
]


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
        pg.wait_for_timeout(4000)
        head = pg.evaluate("document.body ? document.body.innerText.slice(0,150) : 'no body'")
        print("PAGE_HEAD:", head.replace("\n", " | "))
        # force virtual list to render everything
        for _ in range(20):
            pg.evaluate("window.scrollBy(0, 2000)")
            pg.wait_for_timeout(300)
        pg.wait_for_timeout(3000)
        txt = pg.evaluate("document.body.innerText || ''")
        for c in CHECKS:
            print(f"{'OK ' if c in txt else 'MISS'} {c}")
        # dump message-like blocks (question texts and answer heads)
        blocks = pg.evaluate(
            """() => {
              const els = [...document.querySelectorAll('div')];
              const out = [];
              for (const el of els) {
                const t = (el.innerText||'').trim();
                if (t.length > 30 && t.length < 120 && el.children.length === 0) out.push(t);
              }
              return out.slice(0, 60);
            }"""
        )
        print("--- blocks ---")
        for b in blocks:
            print(" *", b[:110].replace("\n", " "))
        b.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
