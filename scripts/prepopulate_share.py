#!/usr/bin/env python3
"""Pre-populate a share-page conversation via the real UI (webbridge).

The API run path does not commit assistant messages to the share session
(pageListLatestMsg stays empty), so we drive the actual page: type, send, wait.

Prereqs: webbridge daemon on 127.0.0.1:10086, browser logged in.
Usage: python prepopulate_share.py [--only 1,2,3,4]
"""

import argparse
import json
import os
import sys
import time
import urllib.request


DAEMON = "http://127.0.0.1:10086/command"
SESSION = "semantic-comms-record"
SHARE_URL = (
    "http://10.128.203.200:30226/agent/index.html"
    "#/arrange/agentExp?randomCode=297d4be1aa2443cca29b62b5be702beb&noLayout=1"
)

QUESTIONS = [
    "什么是语义通信？它和传统通信有什么区别？",
    "Deep JSCC 和 DeepSC 有什么区别？",
    "请画出语义通信系统的架构流程图（mermaid 语法），并简要解释图中各模块的作用。",
    "请联网搜索2025年语义通信领域最新发表的三篇论文，并总结它们的核心贡献。注意：不要编造，如果无法联网请明确说明。",
]


def cmd(action, args=None):
    body = {"action": action, "args": args or {}, "session": SESSION}
    req = urllib.request.Request(
        DAEMON,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def evaluate(code):
    r = cmd("evaluate", {"code": code})
    return (r.get("data") or {}).get("value")


def reset_conversation():
    snap = cmd("snapshot", {})
    refs = []

    def walk(n):
        if isinstance(n, dict):
            if n.get("role") == "button" and "新开对话" in (n.get("name") or ""):
                refs.append(n.get("ref"))
            for c in n.get("children") or []:
                walk(c)
        elif isinstance(n, list):
            for c in n:
                walk(c)

    walk((snap.get("data") or {}).get("tree") or [])
    if refs:
        cmd("click", {"selector": refs[0]})
        time.sleep(4)
        return True
    return False


def clear_input():
    evaluate(
        "(() => { const ta = document.querySelector('textarea'); if (ta) { "
        "const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set; "
        "setter.call(ta, ''); ta.dispatchEvent(new Event('input', {bubbles: true})); return true; } return false; })()"
    )


def click_last_send_button():
    snap = cmd("snapshot", {})
    buttons = []

    def walk(n):
        if isinstance(n, dict):
            if n.get("role") == "button":
                buttons.append(n.get("ref"))
            for c in n.get("children") or []:
                walk(c)
        elif isinstance(n, list):
            for c in n:
                walk(c)

    walk((snap.get("data") or {}).get("tree") or [])
    if not buttons:
        return False
    cmd("click", {"selector": buttons[-1]})
    return True


def send_and_wait(question, timeout=300):
    len0 = len(evaluate("document.body.innerText || ''") or "")
    clear_input()
    time.sleep(0.5)
    evaluate(
        "(() => { const el = document.querySelector('textarea'); if (el) { el.focus(); return true; } return false; })()"
    )
    cmd("cdp", {"method": "Input.insertText", "params": {"text": question}})
    time.sleep(1.5)
    val = evaluate("(() => { const ta = document.querySelector('textarea'); return ta ? ta.value : 'no-ta'; })()")
    if not val:
        raise RuntimeError("input empty after insertText")
    if not click_last_send_button():
        raise RuntimeError("no send button")
    time.sleep(5)
    val2 = evaluate("(() => { const ta = document.querySelector('textarea'); return ta ? ta.value : 'no-ta'; })()")
    if val2:
        print("  (发送未清空输入框，重试)", flush=True)
        click_last_send_button()

    started = time.time()
    last_len = len0
    stable = 0
    while time.time() - started < timeout:
        time.sleep(15)
        text = evaluate("document.body.innerText || ''") or ""
        cur = len(text)
        if cur - len0 > 400 and cur == last_len:
            stable += 1
            if stable >= 3:
                return time.time() - started
        else:
            stable = 0
        last_len = cur
        if cur - len0 > 400 and time.time() - started > 240:
            return time.time() - started
    return time.time() - started


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="1,2,3,4")
    ap.add_argument("--no-reset", action="store_true")
    args = ap.parse_args()
    only = {int(x) for x in args.only.split(",")}

    cmd("navigate", {"url": SHARE_URL, "newTab": True, "group_title": "语义通信助手 Demo"})
    time.sleep(6)
    if not args.no_reset:
        reset_conversation()
    for i, q in enumerate(QUESTIONS, 1):
        if i not in only:
            continue
        print(f"===== Q{i}: {q[:30]}...", flush=True)
        try:
            elapsed = send_and_wait(q)
            print(f"  -> {elapsed:.0f}s", flush=True)
        except Exception as e:
            print(f"  -> FAILED {e}", flush=True)


if __name__ == "__main__":
    main()
