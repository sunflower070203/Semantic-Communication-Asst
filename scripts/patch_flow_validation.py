#!/usr/bin/env python3
"""Apply the citation-validation patch to a specific B-route flow version.

Pulls the flow config for <AGENT_CODE>_<AGENT_VERSION>, patches the meta node
script + summary prompt (logic in flow_patch.py), and writes the saveProcess
payload to flow_validation_payload.json (POST it yourself, or use deploy_flow.py).

Usage: python patch_flow_validation.py [<agent_version>]
"""

import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import flow_patch
from kb_upload import http_json  # shared request helper (no side effects)


def main():
    agent_version = sys.argv[1] if len(sys.argv) > 1 else config.AGENT_VERSION
    url = (
        f"{config.PLATFORM}/api/flow/config/get?configTargetType=AGENT"
        f"&configCode={urllib.parse.quote(config.AGENT_CODE + '_' + agent_version)}"
    )
    cfg = http_json(url)["data"]
    assert cfg.get("status") in ("DRAFT", "DEV"), f"flow not editable: {cfg.get('status')}"
    payload = flow_patch.save_payload(config.AGENT_CODE, agent_version, cfg)
    with open("flow_validation_payload.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    nodes = len(payload["data"]["nodes"])
    edges = len(payload["data"]["edges"])
    print(f"agent_version={agent_version} nodes={nodes} edges={edges} "
          f"meta_script_len={len(flow_patch.NEW_SCRIPT)}")
    print("payload written to flow_validation_payload.json")


if __name__ == "__main__":
    main()
