#!/usr/bin/env python3
"""Shared flow-patch logic for the B-route workflow (citation validation).

Used by patch_flow_validation.py (single version) and deploy_flow.py (clone->patch->online).
"""

import json


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
    if raw is None and not refs:
        problems.append('总结输出无法解析，未能校验')
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

ANTI_FABRICATION_LINE = (
    '* 引用的 idx 必须真实存在于"参考内容"中，禁止编造引用、禁止虚构出处；'
    '如果提供的上下文信息不足，直接声明"很抱歉，信息不足";'
)
MERMAID_LINE = (
    '* 如果问题涉及系统架构、处理流程或结构对比（如语义通信系统框架、JSCC 编解码流程），'
    '请在 answer 末尾附一段 ```mermaid 代码块（flowchart 或 sequenceDiagram 语法）作为图示；'
    '不适合用图时不要输出 mermaid。'
)
PROMPT_ANCHOR = '* 你必须输出符合下方 "输出规范" 部分所述规范的 JSON;'


def build_patched_flow(cfg):
    """Return (nodes, edges) with the citation-validation patch applied."""
    flow = json.loads(cfg["showConfig"])
    nodes = flow["nodes"]
    edges = flow["edges"]

    meta = summary = None
    for n in nodes:
        if n["id"] == META_NODE_ID:
            meta = n
        if n["id"] == SUMMARY_NODE_ID:
            summary = n
    assert meta is not None, "meta node not found"
    assert summary is not None, "summary node not found"

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

    prompt = summary["data"]["config"]["prompt"]
    if "禁止编造引用" not in prompt:
        prompt = prompt.replace(PROMPT_ANCHOR, ANTI_FABRICATION_LINE + "\n" + PROMPT_ANCHOR)
    if "mermaid" not in prompt:
        prompt = prompt.replace(PROMPT_ANCHOR, MERMAID_LINE + "\n" + PROMPT_ANCHOR)
    summary["data"]["config"]["prompt"] = prompt
    return nodes, edges


def save_payload(agent_code, agent_version, cfg):
    nodes, edges = build_patched_flow(cfg)
    return {
        "configTargetType": "AGENT",
        "configCode": f"{agent_code}_{agent_version}",
        "version": cfg["version"],
        "data": {"nodes": nodes, "edges": edges},
    }
