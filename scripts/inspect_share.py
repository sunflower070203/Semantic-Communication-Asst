#!/usr/bin/env python3
"""Dump interactive elements of the share page to locate input + send controls."""

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
        pg.wait_for_timeout(6000)
        els = pg.evaluate(
            """() => {
              const out = [];
              const tags = ['textarea','input','button'];
              for (const t of tags) {
                for (const el of document.querySelectorAll(t)) {
                  const r = el.getBoundingClientRect();
                  out.push({
                    tag: t,
                    cls: (el.className||'').toString().slice(0,60),
                    ph: el.getAttribute('placeholder')||'',
                    text: (el.innerText||el.value||'').toString().slice(0,40),
                    visible: r.width > 0 && r.height > 0,
                    w: Math.round(r.width), h: Math.round(r.height),
                    contenteditable: el.getAttribute('contenteditable')||''
                  });
                }
              }
              return out;
            }"""
        )
        for e in els:
            if e["visible"]:
                print(e)
        b.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
