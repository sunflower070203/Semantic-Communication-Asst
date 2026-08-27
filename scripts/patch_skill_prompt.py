#!/usr/bin/env python3
"""Inject the semantic-communication-expert skill norms into the summary LLM prompt.

OpenTrek's skill binding targets TrekClaw-style agents; workflow agents have no
trekClawSkillList field, so the skill's expert norms are applied at the prompt
level of the summary node instead (same behavior, platform-compatible).

Usage: python patch_skill_prompt.py [--version 1787836399246] [--online]
"""

import argparse
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import flow_patch  # noqa: E402
from kb_upload import http_json  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SUMMARY_NODE_ID = flow_patch.SUMMARY_NODE_ID
PROMPT_ANCHOR = "* 你必须输出符合下方 \"输出规范\" 部分所述规范的 JSON;"

SKILL_NORMS = """* 术语必须使用标准中英文对照：语义通信 Semantic Communication、联合信源信道编码 JSCC、任务导向通信 Task-Oriented Communication、语义噪声 Semantic Noise、语义保真度 Semantic Fidelity、深度语义通信 DeepSC；
* 不要混淆 Deep JSCC（面向图像，MSE/PSNR/SSIM 评估）与 DeepSC（面向文本，交叉熵/BLEU 评估）的适用模态与评估指标；
* 回答后按专家维度自查：术语准确、引用可溯源、不编造、结构清晰、涉及架构/流程时输出 mermaid 图；
* 提供的上下文信息不足时直接声明"很抱歉，信息不足"，不猜测具体数据、实验数值与发表年份；"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="1787836399246", help="agent version to patch")
    ap.add_argument("--online", action="store_true", help="上线被修改的版本")
    args = ap.parse_args()

    code = f"{config.AGENT_CODE}_{args.version}"
    url = (
        f"{config.PLATFORM}/api/flow/config/get?configTargetType=AGENT"
        f"&configCode={urllib.parse.quote(code)}"
    )
    cfg = http_json(url)["data"]
    flow = json.loads(cfg["showConfig"])
    summary = None
    for n in flow["nodes"]:
        if n["id"] == SUMMARY_NODE_ID:
            summary = n
    assert summary is not None, "summary node not found"

    prompt = summary["data"]["config"]["prompt"]
    if "术语必须使用标准中英文对照" not in prompt:
        prompt = prompt.replace(PROMPT_ANCHOR, SKILL_NORMS + "\n" + PROMPT_ANCHOR)
        summary["data"]["config"]["prompt"] = prompt
        payload = {
            "configTargetType": "AGENT",
            "configCode": code,
            "version": cfg["version"],
            "data": {"nodes": flow["nodes"], "edges": flow["edges"]},
        }
        r = http_json(f"{config.PLATFORM}/api/flow/config/saveProcess", method="POST", data=payload)
        if not r.get("success"):
            raise RuntimeError(f"saveProcess failed: {r.get('errorCode')} {r.get('errorMsg')}")
        print(f"prompt patched + saved: {code}")
    else:
        print("prompt already contains skill norms, skipping")

    if args.online:
        r = http_json(
            f"{config.PLATFORM}/agent/version/online",
            method="POST",
            data={"agentCode": config.AGENT_CODE, "agentVersion": args.version},
        )
        print("online:", r.get("success"), r.get("errorMsg"))


if __name__ == "__main__":
    main()
