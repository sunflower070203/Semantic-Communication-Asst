#!/usr/bin/env python3
"""Deterministic unit tests for the deployed citation-validation script.

The platform's `meta` node runs `flow_patch.NEW_SCRIPT` inside a sandbox. This
test executes that exact source against synthetic params and asserts both the
positive path (all refs verified) and negative paths (fabricated ref, missing
marker, invalid JSON, markdown-fenced JSON, refIds fallback).

No platform, no model. Run: python test_validation_logic.py
"""

import sys
from types import SimpleNamespace

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import flow_patch


def _run_script(answer_raw, all_meta, ref_ids):
    ns = {}
    exec(flow_patch.NEW_SCRIPT, ns)
    params = SimpleNamespace(
        answer_raw=answer_raw,
        all_meta=all_meta,
        refIds=ref_ids,
    )
    show = ns["execute_show_content"](params)
    meta = ns["execute_result_meta"](params)
    return show, meta


META = [
    {"refId": 1, "file_code": "A", "chunk_bboxs": None, "sys_data_id": "s1"},
    {"refId": 2, "file_code": "B", "chunk_bboxs": None, "sys_data_id": "s2"},
    {"refId": 3, "file_code": "C", "chunk_bboxs": None, "sys_data_id": "s3"},
]


def test_positive():
    raw = (
        '{"answer": "语义通信关注含义【 I 】与任务【 II 】。", "refs": ['
        '{"idx": 1, "x": "I", "title": "《A》引言"},'
        '{"idx": 2, "x": "II", "title": "《B》系统模型"}]}'
    )
    show, meta = _run_script(raw, META, [])
    assert "⚠" not in show, f"positive path must not warn: {show}"
    assert " I. 《A》引言" in show and " II. 《B》系统模型" in show
    assert len(meta) == 2
    print("PASS positive")


def test_ref_idx_not_in_recall():
    raw = (
        '{"answer": "引用了不存在的来源【 III 】。", "refs": ['
        '{"idx": 99, "x": "III", "title": "《虚构》内容"}]}'
    )
    show, _ = _run_script(raw, META, [])
    assert "⚠" in show and "III(idx=99)" in show, f"must flag fabricated ref: {show}"
    print("PASS ref_idx_not_in_recall")


def test_marker_without_ref():
    raw = (
        '{"answer": "正文标记【 V 】但没有对应 refs。", "refs": ['
        '{"idx": 1, "x": "I", "title": "《A》"}]}'
    )
    show, _ = _run_script(raw, META, [])
    assert "⚠" in show and "V" in show, f"must flag missing marker ref: {show}"
    print("PASS marker_without_ref")


def test_markdown_fenced_json():
    raw = '```json\n{"answer": "语义通信【 I 】", "refs": [{"idx": 1, "x": "I", "title": "《A》"}]}\n```'
    show, _ = _run_script(raw, META, [])
    assert "⚠" not in show and " I. 《A》" in show, f"fence must be tolerated: {show}"
    print("PASS markdown_fenced_json")


def test_invalid_json():
    show, _ = _run_script("这不是 JSON", META, [])
    assert "总结输出无法解析" in show, f"invalid JSON must warn: {show}"
    print("PASS invalid_json")


def test_refids_fallback():
    raw = '{"answer": "仅文本无 refs 字段。"}'
    ref_ids = [{"idx": 1, "x": "I", "title": "《A》"}]
    show, meta = _run_script(raw, META, ref_ids)
    assert " I. 《A》" in show, f"refIds fallback must render: {show}"
    assert len(meta) == 1
    print("PASS refids_fallback")


def main():
    tests = [
        test_positive,
        test_ref_idx_not_in_recall,
        test_marker_without_ref,
        test_markdown_fenced_json,
        test_invalid_json,
        test_refids_fallback,
    ]
    for t in tests:
        t()
    print(f"\nALL {len(tests)} TESTS PASSED")


if __name__ == "__main__":
    main()
