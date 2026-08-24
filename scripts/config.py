#!/usr/bin/env python3
"""Central config for all platform scripts.

Credentials are read from environment variables (or a local, git-ignored `.env`
file at the repo root). Never commit real credentials.
"""

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv():
    dotenv = REPO_ROOT / ".env"
    if not dotenv.exists():
        return
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


def _require(name):
    val = os.environ.get(name, "").strip()
    if not val:
        raise RuntimeError(
            f"缺少环境变量 {name}。请在仓库根目录创建 .env（参考 .env.example），"
            "或通过环境变量注入。"
        )
    return val


PLATFORM = os.environ.get("OPENTREK_PLATFORM", "http://10.128.203.200:30226")
COOKIE = _require("OPENTREK_COOKIE")

# B 路线：语义通信知识问答
AGENT_CODE = os.environ.get("OPENTREK_AGENT_CODE", "fcae0115-ea0f-4c86-b688-56ac9c88db05")
AGENT_VERSION = os.environ.get("OPENTREK_AGENT_VERSION", "1787495161508")
KB_CODE = os.environ.get("OPENTREK_KB_CODE", "ryekr4gqw2pn")

# A 路线：语义通信自主 Agent3（角色对话 / AutoBotV2 / ReAct）
AGENT3_CODE = os.environ.get("OPENTREK_AGENT3_CODE", "407be567-2e47-4391-8249-729d943d1753")
AGENT3_VERSION = os.environ.get("OPENTREK_AGENT3_VERSION", "1787370379269")
