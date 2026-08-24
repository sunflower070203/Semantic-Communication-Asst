#!/usr/bin/env python3
"""Automate the B-route release cycle: clone -> patch -> save -> (optional) online.

The platform freezes ONLINE flow configs, so every change requires cloning a new
version (configCleanSourceEnum=KEEP preserves the flow), patching it, saving,
then publishing. This script does the whole cycle and prints the new version.

Usage:
  python deploy_flow.py [--source-version 1787495161508] [--online] [--name v1.5]

After a successful deploy, update OPENTREK_AGENT_VERSION in .env, run
eval_agent.py to regression-check, and create a new share link.
"""

import argparse
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import flow_patch
from kb_upload import http_json


def clone_version(agent_code, source_version, version_name=None):
    data = {
        "agentCode": agent_code,
        "agentVersion": source_version,
        "configCleanSourceEnum": "KEEP",
    }
    if version_name:
        data["versionName"] = version_name
    r = http_json(
        f"{config.PLATFORM}/agent/version/cloneAndCreateNewVersion",
        method="POST",
        data=data,
    )
    if not r.get("success"):
        raise RuntimeError(f"clone 失败: {r.get('errorCode')} {r.get('errorMsg')}")
    new_version = r["data"]["agentVersion"]
    print(f"clone OK: {source_version} -> {new_version} (status={r['data'].get('agentStatus')})")
    return new_version


def save_flow(agent_code, agent_version):
    url = (
        f"{config.PLATFORM}/api/flow/config/get?configTargetType=AGENT"
        f"&configCode={urllib.parse.quote(agent_code + '_' + agent_version)}"
    )
    cfg = http_json(url)["data"]
    assert cfg.get("status") in ("DRAFT", "DEV"), f"flow not editable: {cfg.get('status')}"
    payload = flow_patch.save_payload(agent_code, agent_version, cfg)
    r = http_json(
        f"{config.PLATFORM}/api/flow/config/saveProcess",
        method="POST",
        data=payload,
    )
    if not r.get("success"):
        raise RuntimeError(f"saveProcess 失败: {r.get('errorCode')} {r.get('errorMsg')}")
    print(f"saveProcess OK: {agent_code}_{agent_version} "
          f"nodes={len(payload['data']['nodes'])} edges={len(payload['data']['edges'])}")
    return r


def online(agent_code, agent_version):
    r = http_json(
        f"{config.PLATFORM}/agent/version/online",
        method="POST",
        data={"agentCode": agent_code, "agentVersion": agent_version},
    )
    if not r.get("success"):
        raise RuntimeError(f"online 失败: {r.get('errorCode')} {r.get('errorMsg')}")
    print(f"online OK: {agent_version}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-version", default=config.AGENT_VERSION)
    ap.add_argument("--online", action="store_true", help="发布后立即上线")
    ap.add_argument("--name", default=None, help="新版本名（默认沿用 v1.0）")
    args = ap.parse_args()

    new_version = clone_version(config.AGENT_CODE, args.source_version, args.name)
    save_flow(config.AGENT_CODE, new_version)
    if args.online:
        online(config.AGENT_CODE, new_version)
    print(f"\n新版本: {new_version}")
    print("下一步: 更新 .env 的 OPENTREK_AGENT_VERSION，跑 eval_agent.py 回归，再建新分享链接。")


if __name__ == "__main__":
    main()
