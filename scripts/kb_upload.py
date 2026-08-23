#!/usr/bin/env python3
"""Upload KB doc files via the OpenTrek API chain:
1. GET /aihub/api/v1/sts?type=upload&path=kortex/kb/doc/file/<name>&fileId=<hash>  -> S3 credentials + object path
2. PUT the file to minio using an AWS SigV4 presigned URL
3. POST /kortex/kb/doc/file/uploadFromPreUploadPaths {kbCode, paths, userMetadata}

Usage:
  python kb_upload.py <kbCode> <file1> [file2 ...]
"""

import hashlib
import hmac
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone


PLATFORM = "http://10.128.203.200:30226"
COOKIE = (
    "G_baseline_gsid=c338c6fbf571426bad461f37517d3fa9-gsid-inner; "
    "G_baseline_accountType=manager; G_baseline_platform=pc; "
    "x-sfm-workspace=606add01-3e5d-4a09-84b7-18b2c2b8f6f8; "
    "projectCode=606add01-3e5d-4a09-84b7-18b2c2b8f6f8; "
    "x-sfm-workspacecode=606add01-3e5d-4a09-84b7-18b2c2b8f6f8; "
    "x-sfm-workspacename=12345; x-sfm-workspace-code=606add01-3e5d-4a09-84b7-18b2c2b8f6f8"
)
IMPORT_PATH = "kortex/kb/doc/file/"


def http_json(url, method="GET", data=None, headers=None):
    req_headers = {"Cookie": COOKIE}
    if headers:
        req_headers.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def uri_escape(s):
    return urllib.parse.quote(s, safe="~")


def sign_v4_presigned_put(creds, object_name):
    """Return presigned PUT URL for minio S3 using AWS SigV4."""
    endpoint = creds["endpoint"].rstrip("/")
    bucket = creds["bucket"]
    access_key = creds["accessKeyId"]
    secret_key = creds["accessKeySecret"]
    token = creds.get("securityToken") or creds.get("stsToken") or ""
    region = creds.get("region") or "default"
    expires = 3600

    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    canonical_uri = "/" + bucket + "/" + "/".join(uri_escape(p) for p in object_name.split("/"))
    query_items = [
        ("X-Amz-Algorithm", "AWS4-HMAC-SHA256"),
        ("X-Amz-Credential", f"{access_key}/{date_stamp}/{region}/s3/aws4_request"),
        ("X-Amz-Date", amz_date),
        ("X-Amz-Expires", str(expires)),
        ("X-Amz-SignedHeaders", "host"),
    ]
    if token:
        query_items.append(("X-Amz-Security-Token", token))
    query_items.sort(key=lambda kv: kv[0])
    canonical_query = "&".join(f"{uri_escape(k)}={uri_escape(v)}" for k, v in query_items)

    parsed = urllib.parse.urlparse(endpoint)
    host = parsed.netloc
    canonical_headers = f"host:{host}\n"
    signed_headers = "host"
    payload_hash = "UNSIGNED-PAYLOAD"

    canonical_request = "\n".join(
        ["PUT", canonical_uri, canonical_query, canonical_headers, signed_headers, payload_hash]
    )
    scope = f"{date_stamp}/{region}/s3/aws4_request"
    string_to_sign = "\n".join(
        ["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical_request.encode()).hexdigest()]
    )

    def _hmac(key, msg):
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    k_date = _hmac(("AWS4" + secret_key).encode("utf-8"), date_stamp)
    k_region = _hmac(k_date, region)
    k_service = _hmac(k_region, "s3")
    k_signing = _hmac(k_service, "aws4_request")
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    query_items.append(("X-Amz-Signature", signature))
    query_items.sort(key=lambda kv: kv[0])
    final_query = "&".join(f"{uri_escape(k)}={uri_escape(v)}" for k, v in query_items)
    return f"{endpoint}{canonical_uri}?{final_query}"


def upload_one(kb_code, file_path, import_prefix=IMPORT_PATH):
    name = file_path.replace("\\", "/").split("/")[-1]
    sts_path = import_prefix + name
    file_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()

    # 1. STS credentials
    q = urllib.parse.urlencode({"type": "upload", "path": sts_path, "fileId": file_id})
    sts = http_json(f"{PLATFORM}/aihub/api/v1/sts?{q}")["data"]
    object_name = sts["path"]
    print(f"[{name}] STS ok -> object: {object_name}")

    # 2. Presigned PUT
    presigned = sign_v4_presigned_put(sts, object_name)
    with open(file_path, "rb") as f:
        payload = f.read()
    print(f"[{name}] PUT {len(payload)} bytes...")
    req = urllib.request.Request(presigned, data=payload, method="PUT")
    with urllib.request.urlopen(req, timeout=600) as resp:
        put_status = resp.status
        print(f"[{name}] PUT status {put_status}")

    # 3. Register
    reg = http_json(
        f"{PLATFORM}/kortex/kb/doc/file/uploadFromPreUploadPaths",
        method="POST",
        data={"kbCode": kb_code, "paths": [object_name], "userMetadata": {}},
    )
    print(f"[{name}] register: {json.dumps(reg, ensure_ascii=False)[:300]}")
    return reg


def main():
    kb_code = sys.argv[1]
    files = sys.argv[2:]
    for fp in files:
        try:
            upload_one(kb_code, fp)
        except Exception as e:
            print(f"[{fp}] FAILED: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
