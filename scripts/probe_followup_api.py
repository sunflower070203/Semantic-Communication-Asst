#!/usr/bin/env python3
"""Same-session follow-up probe: ask Q, then ask a follow-up in the SAME session.

Verifies cross-turn context (multi-turn agent behavior) on the B-route agent.

Usage: python probe_followup_api.py
Output: demo/probes/probe_followup_api.md/.json
"""

import json
import os
import sys
import threading
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_demo_qa as m


def main():
    sid = m.create_session()
    client = "followup-api"
    stop = threading.Event()
    sse = m.SseThread(sid, client, stop)
    sse.start()
    deadline = time.time() + 15
    while time.time() < deadline and not sse.first_lines:
        time.sleep(0.5)

    q1 = "什么是语义通信？它和传统通信有什么区别？"
    q2 = "你刚才提到了语义鸿沟，具体指什么？能结合论文展开讲讲吗？"
    tasks1, t1, a1 = m.run_question(sid, client, q1, timeout=420)
    tasks2, t2, a2 = m.run_question(sid, client, q2, timeout=420)
    stop.set()

    out = {
        "session": sid,
        "q1": q1, "q1_answer": a1, "q1_elapsed_s": round(t1, 1),
        "q2": q2, "q2_answer": a2, "q2_elapsed_s": round(t2, 1),
        "q2_recall_sources": m.fetch_recall_sources(tasks2),
        "q2_task_types": [t.get("typeCode") for t in tasks2],
        "context_used": "语义鸿沟" in a2 and "语义" in a2,
    }
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo", "probes")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "probe_followup_api.md"), "w", encoding="utf-8") as f:
        f.write(
            "# Probe followup (API, same session)\n\n"
            f"- 时间: {datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            f"- 上下文复用: {out['context_used']}\n\n"
            f"## Q1\n\n{q1}\n\n### A1（{t1:.0f}s）\n\n{a1}\n\n"
            f"## Q2（同会话追问）\n\n{q2}\n\n### A2（{t2:.0f}s）\n\n{a2}\n"
        )
    with open(os.path.join(out_dir, "probe_followup_api.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"Q1: {t1:.0f}s {len(a1)} chars | Q2: {t2:.0f}s {len(a2)} chars | context_used={out['context_used']}", flush=True)


if __name__ == "__main__":
    main()
