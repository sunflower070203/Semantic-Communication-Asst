#!/usr/bin/env python3
"""Add citation-validation + anti-fabrication to the B-route workflow.

Changes:
1. meta node: new input `answer_raw` (raw summary JSON) + extended script:
   - every ref idx must exist in the recalled chunks (all_meta)
   - every 【X】 marker in the answer must exist in refs
   - unverifiable citations are appended as "⚠ 引用校验：..." footer
2. 结果总结 LLM prompt: forbid fabricating refs; if info insufficient, say so.

Usage: python patch_flow_validation.py
"""

import json
import urllib.parse
import urllib.request


PLATFORM = "http://10.128.203.200:30226"
COOKIE = (
    "G_baseline_gsid=c338c6fbf571426bad461f37517d3fa9-gsid-inner; "
    "G_baseline_accountType=manager; G_baseline_platform=pc; "
    "x-sfm-workspace=606add01-3e5d-4a09-84b7-18b2c2b8f6f8; "
    "projectCode=606add01-3e5d-4a09-84b7-18b2c2b8f6f8; "
    "x-sfm-workspacecode=606add01-3e5d-4a09-84b7-18b2c2b8f6f8; "
    "x-sfm-workspacename=12345; x-sfm-workspace-code=606add01-3e5d-4a09-84b7-18b2c2b8f6f8"
)
AGENT_CODE = "fcae0115-ea0f-4c86-b688-56ac9c88db05"
AGENT_VERSION = "1787495161508"  # v1.4 clone (DEV) - editable

META_NODE_ID = "node_Y7WTZS09WndVv6J4"
SUMMARY_NODE_ID = "node_NVF6CdTT4Wy0AVtl"

NEW_SCRIPT = '''def parse_refs_data(params):
    import json as jsonmod
    raw_text = params.answer_raw or '{}'
    raw_text = raw_text.strip()
    if raw_text.startswith('```'):
        raw_text = raw_text.strip('`').strip()
        if raw_text.startswith('json'):
            raw_text = raw_text[4:].strip()
    a = raw_text.find('{')
    b = raw_text.rfind('}')
    if a >= 0 and b > a:
        raw_text = raw_text[a:b + 1]
    try:
        raw = jsonmod.loads(raw_text)
    except Exception:
        return None
    return raw

def execute_result_meta(params):
    raw = parse_refs_data(params)
    refs = (raw or {}).get('refs') or []
    if not refs:
        refs = params.refIds or []
    ref_map = {}
    for temp in refs:
        ref_map[temp['idx']] = temp['title']
    result_meta = []
    for obj in params.all_meta:
        if ref_map.get(obj['refId']) is not None:
            result_meta.append(obj)
    return result_meta

def execute_show_content(params):
    import json as jsonmod
    import re as remod
    raw = parse_refs_data(params)
    refs = (raw or {}).get('refs') or []
    if not refs:
        refs = params.refIds or []
    answer_text = (raw or {}).get('answer') or ''
    problems = []
    try:
        meta_ids = set()
        for m in (params.all_meta or []):
            meta_ids.add(m.get('refId'))
        ref_romans = set()
        for r in refs:
            ref_romans.add(r.get('x'))
            if r.get('idx') not in meta_ids:
                problems.append(str(r.get('x')) + '(idx=' + str(r.get('idx')) + ')')
        markers = remod.findall(r'[【\\[]\\s*([IVXLCDM]+)\\s*[】\\]]', answer_text)
        for m in markers:
            if m not in ref_romans:
                problems.append(m)
    except Exception:
        problems.append('总结输出无法解析，未能校验')
    str_ret = ''
    for temp in refs:
        str_ret += f"\\n {temp['x']}. {temp['title']}"
    if problems:
        seen = []
        for p in problems:
            if p not in seen:
                seen.append(p)
        str_ret += '\\n\\n> ⚠ 引用校验：[' + ','.join(seen) + '] 未能与本次召回内容核实'
    return str_ret'''


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


def main():
    url = (
        f"{PLATFORM}/api/flow/config/get?configTargetType=AGENT"
        f"&configCode={urllib.parse.quote(AGENT_CODE + '_' + AGENT_VERSION)}"
    )
    cfg = http_json(url)["data"]
    flow_version = cfg["version"]
    assert cfg.get("status") in ("DRAFT", "DEV"), f"flow not editable: {cfg.get('status')}"
    flow = json.loads(cfg["showConfig"])
    nodes = flow["nodes"]
    edges = flow["edges"]

    meta = None
    summary = None
    for n in nodes:
        if n["id"] == META_NODE_ID:
            meta = n
        if n["id"] == SUMMARY_NODE_ID:
            summary = n
    assert meta is not None, "meta node not found"
    assert summary is not None, "summary node not found"

    # 1) meta: replace script + add answer_raw input mapping
    meta["data"]["config"]["scriptContent"] = NEW_SCRIPT
    in_mappings = meta["data"].get("inMappings") or []
    names = {m.get("name") for m in in_mappings}
    if "answer_raw" not in names:
        in_mappings.append(
            {
                "desc": "",
                "editable": True,
                "mappingTree": {
                    "children": [
                        {
                            "children": [
                                {
                                    "desc": "返回内容",
                                    "hasChildren": False,
                                    "name": "content",
                                    "valueType": "SSTRING",
                                }
                            ],
                            "desc": "结果总结",
                            "hasChildren": True,
                            "name": SUMMARY_NODE_ID,
                            "valueType": "OBJECT",
                        }
                    ],
                    "desc": "节点",
                    "hasChildren": True,
                    "name": "NODE",
                },
                "name": "answer_raw",
                "necessary": False,
                "refType": "REF",
                "subMappings": [],
                "valueType": "SSTRING",
            }
        )
    meta["data"]["inMappings"] = in_mappings

    # 2) summary prompt: forbid fabricated refs
    prompt = summary["data"]["config"]["prompt"]
    anti = (
        '* 引用的 idx 必须真实存在于"参考内容"中，禁止编造引用、禁止虚构出处；'
        '如果提供的上下文信息不足，直接声明"很抱歉，信息不足";'
    )
    if "禁止编造引用" not in prompt:
        prompt = prompt.replace(
            '* 你必须输出符合下方 "输出规范" 部分所述规范的 JSON;',
            anti + '\n* 你必须输出符合下方 "输出规范" 部分所述规范的 JSON;',
        )
    summary["data"]["config"]["prompt"] = prompt

    payload = {
        "configTargetType": "AGENT",
        "configCode": f"{AGENT_CODE}_{AGENT_VERSION}",
        "version": flow_version,
        "data": {"nodes": nodes, "edges": edges},
    }
    with open("flow_validation_payload.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f"nodes={len(nodes)} edges={len(edges)} meta_script_len={len(NEW_SCRIPT)}")
    print("prompt_has_anti_fabrication:", "禁止编造引用" in summary["data"]["config"]["prompt"])
    print("payload written to flow_validation_payload.json")


if __name__ == "__main__":
    main()
