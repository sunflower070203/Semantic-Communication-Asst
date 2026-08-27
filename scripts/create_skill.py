#!/usr/bin/env python3
"""Package + upload + scan + create the semantic-communication-expert skill."""

import json
import os
import sys
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
from kb_upload import http_json  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "skills", "semantic-communication-expert")
ZIP = os.path.join(ROOT, "demo", "semantic-communication-expert.zip")
SKILL_NAME = "semantic-communication-expert"


def make_zip():
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(SRC, SKILL_NAME + "/")
        for root, dirs, files in os.walk(SRC):
            for d in sorted(dirs):
                full = os.path.join(root, d)
                z.write(full, os.path.relpath(full, SRC).replace(os.sep, "/"))
            for f in sorted(files):
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, SRC).replace(os.sep, "/"))
    print("zip:", ZIP, os.path.getsize(ZIP), "bytes")


def upload_zip():
    r = http_json(
        f"{config.PLATFORM}/media/getSkillMediaOSSPolicyByName?fileName={SKILL_NAME}.zip"
    )
    data = r["data"]
    presign = data["preSignedUrl"]
    with open(ZIP, "rb") as f:
        body = f.read()
    req = urllib.request.Request(
        presign, data=body, method="PUT", headers={"Content-Type": "application/zip"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        assert resp.status == 200, resp.status
    zip_url = data["downloadUrl"]  # keep the full presigned URL for server-side fetch
    print("uploaded:", zip_url)
    return zip_url


def scan_zip(zip_url):
    r = http_json(
        f"{config.PLATFORM}/agent/api/skill/scanZip", method="POST", data={"zipUrl": zip_url}
    )
    if not r.get("success"):
        raise RuntimeError(f"scanZip failed: {r.get('errorCode')} {r.get('errorMsg')}")
    print("scan OK:", json.dumps(r["data"], ensure_ascii=False)[:500])
    return r["data"]


def create_skill(scan_data, zip_url):
    payload = {
        "name": SKILL_NAME,
        "zipUrl": zip_url,
        "skillType": "FILE",
    }
    # merge scan-provided fields (description, descriptionZh, category, allowedTools...)
    if isinstance(scan_data, dict):
        for k in ("description", "descriptionZh", "category", "allowedTools", "skillMd", "exampleQuestions"):
            if k in scan_data and scan_data[k] not in (None, ""):
                payload[k] = scan_data[k]
    r = http_json(f"{config.PLATFORM}/agent/api/skill/create", method="POST", data=payload)
    if not r.get("success"):
        raise RuntimeError(f"create failed: {r.get('errorCode')} {r.get('errorMsg')}")
    print("create OK:", json.dumps(r["data"], ensure_ascii=False)[:400])
    return r["data"]


def main():
    make_zip()
    zip_url = upload_zip()
    scan = scan_zip(zip_url)
    create_skill(scan, zip_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
