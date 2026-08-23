#!/usr/bin/env python3
"""Deterministic eval for the B-route agent (harness regression suite).

Runs a fixed scenario set against the ONLINE agent and asserts:
  A. answer present, non-trivial, not the welcome message
  B. no flow/script execution error leaked into the answer
  C. every 【X】 citation marker in the answer body has a refs entry
  D. citation validation passed (no "⚠ 引用校验" unverified footer)
  E. tool-require scenario refuses instead of fabricating
  F. no task ended in ERROR/FAILED

Usage: python eval_agent.py [--questions 1,2,3] [--timeout 420]
Exit code: 0 all pass, 1 any fail.
"""

import argparse
import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_demo_qa as m


SCENARIOS = [
    {
        "id": "concept",
        "question": "什么是语义通信？它和传统通信有什么区别？",
        "require_refusal": False,
    },
    {
        "id": "multistep",
        "question": "请先解释 Deep JSCC 的核心思想，然后对比它和传统分离式信源信道编码在性能上的差异，最后基于分析给出一个最值得做的改进方向，并说明理由。",
        "require_refusal": False,
    },
    {
        "id": "tool_require",
        "question": "请联网搜索2025年语义通信领域最新发表的三篇论文，并总结它们的核心贡献。注意：不要编造，如果无法联网请明确说明。",
        "require_refusal": True,
    },
]

WELCOME_MARKERS = ("请问您需要了解哪方面的信息", "我能为您提供", "很高兴为您服务")
REF_MARKER_RE = re.compile(r"[【\[]\s*([IVXLCDM]+)\s*[】\]]")


def split_body_refs(answer):
    """Split final answer into body and trailing refs list at '----'."""
    if "----" in answer:
        body, refs = answer.split("----", 1)
    else:
        body, refs = answer, ""
    return body, refs


def evaluate_one(scenario, timeout=420):
    sid = m.create_session()
    client = f"eval-{scenario['id']}"
    stop = threading.Event()
    sse = m.SseThread(sid, client, stop)
    sse.start()
    deadline = time.time() + 15
    while time.time() < deadline and not sse.first_lines:
        time.sleep(0.5)
    tasks, elapsed, answer = m.run_question(sid, client, scenario["question"], timeout=timeout)
    stop.set()
    if not answer:
        answer = m.fetch_answer(sid)

    checks = {}
    checks["answer_present"] = len(answer) > 60 and not any(w in answer for w in WELCOME_MARKERS)
    checks["no_flow_error"] = "FLOW_SCRIPT_EXECUTE_ERROR" not in answer and "脚本任务执行异常" not in answer

    body, refs = split_body_refs(answer)
    body_markers = set(REF_MARKER_RE.findall(body))
    ref_markers = set(re.findall(r"(?m)(?:^|\s)([IVXLCDM]+)[\.、:]", refs))
    checks["markers_in_refs"] = body_markers.issubset(ref_markers)
    checks["validation_clean"] = "⚠ 引用校验" not in answer

    if scenario["require_refusal"]:
        checks["refused"] = any(
            k in answer
            for k in ("无法", "很抱歉，信息不足", "信息不足", "未能", "不具备", "实时联网检索")
        )
    else:
        checks["refused"] = True

    checks["no_task_failure"] = all(t.get("status") != "ERROR" and t.get("status") != "FAILED" for t in tasks)
    passed = all(checks.values())
    return {
        "id": scenario["id"],
        "question": scenario["question"],
        "elapsed_s": round(elapsed, 1),
        "answer": answer,
        "checks": checks,
        "passed": passed,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", help="comma-separated scenario indices (1-based)")
    ap.add_argument("--timeout", type=int, default=420)
    args = ap.parse_args()

    only = {int(x) for x in args.questions.split(",")} if args.questions else None
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo", "eval")
    os.makedirs(out_dir, exist_ok=True)

    results = []
    transient = lambda r: not r["checks"]["answer_present"] or not r["checks"]["no_task_failure"]
    for i, sc in enumerate(SCENARIOS, 1):
        if only and i not in only:
            continue
        print(f"===== eval {i} {sc['id']}", flush=True)
        r = evaluate_one(sc, timeout=args.timeout)
        if not r["passed"] and transient(r):
            print(f"  -> transient failure ({r['elapsed_s']}s), retrying once", flush=True)
            r = evaluate_one(sc, timeout=args.timeout)
        results.append(r)
        with open(os.path.join(out_dir, f"case_{r['id']}.json"), "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
        print(f"  -> {'PASS' if r['passed'] else 'FAIL'} {r['elapsed_s']}s {json.dumps(r['checks'], ensure_ascii=False)}", flush=True)

    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    report = os.path.join(out_dir, f"eval_report_{stamp}.md")
    with open(report, "w", encoding="utf-8") as f:
        f.write(f"# Agent Eval Report {stamp}\n\n")
        f.write(f"agent: {m.AGENT_CODE} / {m.AGENT_VERSION}\n\n")
        for r in results:
            f.write(f"## {r['id']} — {'PASS' if r['passed'] else 'FAIL'} ({r['elapsed_s']}s)\n\n")
            f.write("| check | result |\n|---|---|\n")
            for k, v in r["checks"].items():
                f.write(f"| {k} | {'✅' if v else '❌'} |\n")
            f.write(f"\n回答片段：\n\n{r['answer'][:800]}\n\n---\n\n")
        all_pass = all(r["passed"] for r in results)
        f.write(f"\n## 汇总：{'ALL PASS' if all_pass else 'HAS FAILURES'}\n")
    print(f"\nReport: {report}")
    print("RESULT:", "ALL PASS" if all(r["passed"] for r in results) else "FAILURES")
    sys.exit(0 if all(r["passed"] for r in results) else 1)


if __name__ == "__main__":
    main()
