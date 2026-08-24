#!/usr/bin/env python3
"""Run the B-route demo Q&A set against the semantic-comm KB agent and save results.

For each question:
  1. POST /designer/createRunningSession -> uniqueCode
  2. open SSE /designer/createCmdChannelNew (background thread)
  3. POST /designer/run {sessionId, input, clientId}
  4. poll /designer/listTask until every task FINISHED
  5. GET /designer/pageListLatestMsg -> final assistant answer blocks
  6. write demo/results/qa_<n>_<slug>.md (+ .json + citations + recall sources)

Usage: python run_demo_qa.py [--only N,M] [--timeout 300]
"""

import argparse
import json
import os
import re
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

PLATFORM = config.PLATFORM
COOKIE = config.COOKIE
AGENT_CODE = config.AGENT_CODE
AGENT_VERSION = config.AGENT_VERSION
KB_CODE = config.KB_CODE

QUESTIONS = [
    "什么是语义通信？它和传统通信有什么区别？",
    "Deep JSCC 的核心思想是什么？它是如何工作的？",
    "Deep JSCC 和 DeepSC 有什么区别？",
    "语义通信目前面临哪些主要挑战？",
    "什么是任务导向通信（task-oriented communication）？和经典通信范式有什么不同？",
    "SNR 自适应的深度联合信源信道编码是如何实现的？",
]


def http_json(url, method="GET", data=None, headers=None, timeout=90):
    req_headers = {"Cookie": COOKIE}
    if headers:
        req_headers.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def slugify(text, n):
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text).strip("-")[:28]
    return f"qa_{n:02d}_{s}"


def create_session():
    r = http_json(
        f"{PLATFORM}/designer/createRunningSession",
        method="POST",
        data={"agentCode": AGENT_CODE, "agentVersion": AGENT_VERSION},
    )
    sid = r["data"]["uniqueCode"]
    return sid


class SseThread(threading.Thread):
    def __init__(self, session_id, client_id, stop_event):
        super().__init__(daemon=True)
        self.session_id = session_id
        self.client_id = client_id
        self.stop = stop_event
        self.first_lines = []

    def run(self):
        url = f"{PLATFORM}/designer/createCmdChannelNew?sessionId={self.session_id}&clientId={self.client_id}"
        req = urllib.request.Request(url, headers={"Cookie": COOKIE})
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                for raw in resp:
                    if self.stop.is_set():
                        break
                    line = raw.decode("utf-8", "ignore").strip()
                    if line.startswith("data:") and len(self.first_lines) < 3:
                        self.first_lines.append(line[:120])
        except Exception as e:
            self.first_lines.append(f"SSE-ERR: {e}")


WELCOME_MARKERS = ("请问您需要了解哪方面的信息", "我能为您提供", "很高兴为您服务")


def run_question(sid, client_id, question, timeout=360):
    run_resp = http_json(
        f"{PLATFORM}/designer/run",
        method="POST",
        data={"sessionId": sid, "input": question, "clientId": client_id},
    )
    if not run_resp.get("success") or run_resp.get("errorCode"):
        print(
            f"[run_question] run 启动失败: {run_resp.get('errorCode')} "
            f"{run_resp.get('errorMsg') or run_resp.get('errorMessage')}",
            file=sys.stderr,
        )
        return [], 0.0, ""
    started = time.time()
    tasks = []
    baseline = fetch_answer(sid)
    answer = baseline
    while time.time() - started < timeout:
        time.sleep(10)
        try:
            r = http_json(
                f"{PLATFORM}/designer/listTask",
                method="POST",
                data={"sessionId": sid, "clientId": client_id},
            )
            tasks = r.get("data") or []
        except Exception:
            tasks = []
        answer = fetch_answer(sid)
        is_real = (
            answer != baseline
            and len(answer) > 60
            and not any(mk in answer for mk in WELCOME_MARKERS)
        )
        if is_real:
            return tasks, time.time() - started, answer
        if any(t.get("status") in ("ERROR", "FAILED", "CANCELED") for t in tasks):
            return tasks, time.time() - started, answer
    return tasks, time.time() - started, answer


def fetch_answer(sid):
    r = http_json(
        f"{PLATFORM}/designer/pageListLatestMsg?sessionCode={sid}&pageIndex=0&pageSize=50",
    )
    msgs = (r.get("data") or {}).get("list") or []
    answer = ""
    for m in msgs:
        if m.get("isRightShow"):
            continue
        blocks = m.get("blocks") or []
        text = "".join((b.get("blockContent") or "") for b in blocks).strip()
        if text:
            answer = text
    return answer


def fetch_recall_sources(tasks):
    """Return {file_name: score} from KNOWLEDGES_DOC task results."""
    name_map = {}
    try:
        fl = http_json(
            f"{PLATFORM}/kortex/kb/doc/file/list",
            method="POST",
            data={"kbCode": KB_CODE, "current": 1, "pageSize": 50},
        )
        for x in (fl.get("data") or {}).get("list") or []:
            name_map[x.get("fileCode")] = x.get("fileOriginalName")
    except Exception:
        pass
    sources = {}
    for t in tasks:
        if t.get("typeCode") != "KNOWLEDGES_DOC":
            continue
        after = t.get("taskAfterTreatmentResult")
        if isinstance(after, dict) and after.get("data"):
            for item in after["data"]:
                fc = item.get("file_code")
                name = name_map.get(fc, fc)
                sources[name] = max(sources.get(name, 0), item.get("score", 0))
    return sources


def fetch_recall_texts(tasks):
    """Return all recalled chunk texts (for grounding checks)."""
    texts = []
    for t in tasks:
        if t.get("typeCode") != "KNOWLEDGES_DOC":
            continue
        after = t.get("taskAfterTreatmentResult")
        if isinstance(after, dict) and after.get("data"):
            for item in after["data"]:
                text = item.get("chunk_content") or item.get("show_content") or ""
                if text:
                    texts.append(text)
    return texts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated 1-based question indices")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    only = None
    if args.only:
        only = {int(x) for x in args.only.split(",")}

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo", "results")
    os.makedirs(out_dir, exist_ok=True)
    index_rows = []

    for n, q in enumerate(QUESTIONS, 1):
        if only and n not in only:
            continue
        print(f"\n===== Q{n}: {q}", flush=True)
        sid = create_session()
        client_id = f"demo-qa-{n}"
        stop = threading.Event()
        sse = SseThread(sid, client_id, stop)
        sse.start()
        deadline = time.time() + 15
        while time.time() < deadline and not sse.first_lines:
            time.sleep(0.5)
        tasks, elapsed, answer = run_question(sid, client_id, q, timeout=args.timeout)
        stop.set()
        if not answer:
            answer = fetch_answer(sid)
        sources = fetch_recall_sources(tasks)

        slug = slugify(q, n)
        md_path = os.path.join(out_dir, f"{slug}.md")
        json_path = os.path.join(out_dir, f"{slug}.json")
        ok = bool(answer and len(answer) > 40)
        status = "OK" if ok else "EMPTY/TIMEOUT"

        header = (
            f"# Q{n}: {q}\n\n"
            f"- 状态: {status} | 用时: {elapsed:.0f}s | 时间: "
            f"{datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            f"- 召回来源: {', '.join(f'{k}({v:.2f})' for k, v in sorted(sources.items())) if sources else '无'}\n\n"
            "## 回答\n\n"
        )
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(header + (answer if answer else "(无有效回答)") + "\n")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "question": q,
                    "answer": answer,
                    "elapsed_s": round(elapsed, 1),
                    "sources": sources,
                    "task_count": len(tasks),
                    "task_statuses": [t.get("status") for t in tasks],
                    "status": status,
                },
                f,
                ensure_ascii=False,
                indent=1,
            )
        index_rows.append((n, status, round(elapsed), q, os.path.basename(md_path)))
        print(f"  -> {status} {elapsed:.0f}s | answer {len(answer)} chars | sources {len(sources)}", flush=True)

    with open(os.path.join(out_dir, "qa_index.md"), "w", encoding="utf-8") as f:
        f.write("# 语义通信助手 · 演示问答结果（自动生成，请勿手改）\n\n")
        f.write("| # | 状态 | 用时 | 问题 | 结果文件 |\n|---|---|---|---|---|\n")
        for n, st, sec, q, fn in index_rows:
            f.write(f"| {n} | {st} | {sec}s | {q} | [{fn}]({fn}) |\n")
    print(f"\nSaved to {out_dir}")


if __name__ == "__main__":
    main()
