#!/usr/bin/env python3
"""Fetch OpenTrek cookies from the webbridge browser and persist them locally.

Writes:
  - scripts/.opentrek_cookies.json  (structured, for Playwright injection)
  - .env  OPENTREK_COOKIE           (header string, for API calls)
"""

import json
import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DAEMON = "http://127.0.0.1:10086/command"
SESSION = "demo-cookie-20260827"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COOKIE_JSON = os.path.join(HERE, ".opentrek_cookies.json")
ENV_PATH = os.path.join(ROOT, ".env")
PLATFORM = "10.128.203.200:30226"


def req(action, args=None):
    body = {"action": action, "args": args or {}, "session": SESSION}
    r = urllib.request.Request(
        DAEMON,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    # ensure the session has a tab so Network.getAllCookies has a target
    tabs = req("list_tabs")
    if not (tabs.get("data") or {}).get("tabs"):
        nav = req("navigate", {"url": f"http://{PLATFORM}/agent/index.html", "newTab": True})
        if not nav.get("data", {}).get("success"):
            print("NAV FAIL", nav)
            return 1

    out = req("cdp", {"method": "Network.getAllCookies", "params": {}})
    if not out.get("ok"):
        print("CDP FAIL", out)
        return 1
    all_cookies = (out.get("data") or {}).get("cookies") or []
    picked = [
        {
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"],
            "path": c.get("path", "/"),
            "secure": bool(c.get("secure")),
            "httpOnly": bool(c.get("httpOnly")),
            "sameSite": c.get("sameSite") or "Lax",
            "expires": c.get("expires", -1),
        }
        for c in all_cookies
        if "10.128.203.200" in c.get("domain", "") or "10.128.6.213" in c.get("domain", "")
    ]
    if not picked:
        print("NO PLATFORM COOKIES FOUND (is the browser logged in?)")
        return 1

    with open(COOKIE_JSON, "w", encoding="utf-8") as f:
        json.dump(picked, f, ensure_ascii=False, indent=1)

    header = "; ".join(f"{c['name']}={c['value']}" for c in picked)
    env_txt = open(ENV_PATH, encoding="utf-8").read()
    env_txt = re.sub(r"(?m)^OPENTREK_COOKIE=.*$", "OPENTREK_COOKIE=" + header, env_txt)
    open(ENV_PATH, "w", encoding="utf-8").write(env_txt)

    print(f"OK: {len(picked)} cookies -> {COOKIE_JSON}")
    print("names:", ", ".join(c["name"] for c in picked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
