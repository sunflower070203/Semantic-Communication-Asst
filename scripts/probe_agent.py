#!/usr/bin/env python3
"""Adversarial probes against the B-route agent (GAN discriminator role).

Runs one or more hostile questions and saves raw answers + task traces
so we can judge whether the system behaves like an agent or a chatbot.

Usage: python probe_agent.py <tag> <question> [<tag> <question> ...]
Output: demo/probes/probe_<tag>.md/.json
"""

import json
import os
import sys
import threading
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_demo_qa as m


def probe(tag, question, timeout=420):
    sid = m.create_session()
    client = f"probe-{tag}"
    stop = threading.Event()
    sse = m.SseThread(sid, client, stop)
    sse.start()
    deadline = time.time() + 15
    while time.time() < deadline and not sse.first_lines:
        time.sleep(0.5)
    tasks, elapsed, answer = m.run_question(sid, client, question, timeout=timeout)
    stop.set()
    if not answer:
        answer = m.fetch_answer(sid)
    sources = m.fetch_recall_sources(tasks)
    return {
        "tag": tag,
        "question": question,
        "answer": answer,
        "elapsed_s": round(elapsed, 1),
        "sources": sources,
        "task_statuses": [t.get("status") for t in tasks],
        "task_types": [t.get("typeCode") for t in tasks],
    }


def main():
    pairs = []
    for i in range(1, len(sys.argv), 2):
        pairs.append((sys.argv[i], sys.argv[i + 1]))
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo", "probes")
    os.makedirs(out_dir, exist_ok=True)
    for tag, q in pairs:
        print(f"===== probe {tag}: {q}", flush=True)
        r = probe(tag, q)
        md = os.path.join(out_dir, f"probe_{tag}.md")
        js = os.path.join(out_dir, f"probe_{tag}.json")
        with open(md, "w", encoding="utf-8") as f:
            f.write(
                f"# Probe {tag}\n\n"
                f"- 时间: {datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
                f"- 用时: {r['elapsed_s']}s | 任务数: {len(r['task_types'])} | 任务类型: {r['task_types']}\n"
                f"- 召回来源: {json.dumps(r['sources'], ensure_ascii=False)}\n\n"
                f"## 问题\n\n{r['question']}\n\n## 回答\n\n{r['answer'] or '(空)'}\n"
            )
        with open(js, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
        print(f"  -> {r['elapsed_s']}s | answer {len(r['answer'])} chars | tasks {r['task_types']} | sources {len(r['sources'])}", flush=True)


if __name__ == "__main__":
    main()
