"""语义通信文献检索节点（自包含脚本）。

平台脚本节点输入（JSON 字符串）:
  {"keywords": ["semantic communication"], "year_from": 2023, "max_results": 5}

输出（JSON 字符串）:
  成功: {"ok": true, "count": N, "papers": [{"title","authors","year","abstract","url","source","citation_count"}]}
  失败: {"ok": false, "error": "<分类>", "message": "<说明>"}

错误分类: param_error（参数非法）/ network_error（网络/超时）/ parse_error（响应解析失败）

注意：粘贴到平台脚本节点时，删除文件末尾的 __main__ 块（平台禁止 __name__），
保留 execute_output 入口。
"""
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

ARXIV_API = "http://export.arxiv.org/api/query"
OPENALEX_API = "https://api.openalex.org/works"
REQUEST_TIMEOUT = 15
MAX_ABSTRACT_CHARS = 600
ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}


@dataclass(frozen=True)
class Query:
    keywords: tuple
    year_from: int
    max_results: int


@dataclass(frozen=True)
class Paper:
    title: str
    authors: tuple
    year: int
    abstract: str
    url: str
    source: str
    citation_count: int

    def to_dict(self):
        return {
            "title": self.title,
            "authors": list(self.authors),
            "year": self.year,
            "abstract": self.abstract[:MAX_ABSTRACT_CHARS],
            "url": self.url,
            "source": self.source,
            "citation_count": self.citation_count,
        }


def parse_query(raw: Any) -> Query:
    if not isinstance(raw, dict):
        raise ValueError("入参必须是 JSON 对象")
    unknown = set(raw) - {"keywords", "year_from", "max_results"}
    if unknown:
        raise ValueError(f"非法字段: {sorted(unknown)}")
    kws = raw.get("keywords")
    if not isinstance(kws, list) or not kws:
        raise ValueError("keywords 必须是非空数组")
    cleaned = []
    for k in kws:
        if not isinstance(k, str):
            raise ValueError("keywords 元素必须是字符串")
        k = k.strip()
        if not k:
            continue
        if len(k) > 100:
            raise ValueError("关键词过长（>100 字符）")
        cleaned.append(k)
    if not cleaned:
        raise ValueError("keywords 不能全为空字符串")
    cleaned = list(dict.fromkeys(cleaned))[:5]
    year = raw.get("year_from", 2023)
    if not isinstance(year, int) or isinstance(year, bool) or not (1900 <= year <= 2030):
        raise ValueError(f"year_from 越界: {year!r}")
    max_results = raw.get("max_results", 5)
    if not isinstance(max_results, int) or isinstance(max_results, bool) or not (1 <= max_results <= 20):
        raise ValueError(f"max_results 越界: {max_results!r}")
    return Query(tuple(cleaned), year, max_results)


def build_arxiv_query(q: Query) -> str:
    parts = [f'abs:"{k}"' for k in q.keywords]
    return " AND ".join(parts)


def parse_arxiv_entry(entry) -> Paper:
    title = re.sub(r"\s+", " ", (entry.findtext("a:title", default="", namespaces=ATOM_NS) or "")).strip()
    published = entry.findtext("a:published", default="", namespaces=ATOM_NS) or ""
    year = int(published[:4]) if re.match(r"\d{4}", published) else 2000
    authors = tuple(
        a.findtext("a:name", default="", namespaces=ATOM_NS)
        for a in entry.findall("a:author", namespaces=ATOM_NS)
        if a.findtext("a:name", default="", namespaces=ATOM_NS)
    )
    url = ""
    for link in entry.findall("a:link", namespaces=ATOM_NS):
        if link.get("rel") == "alternate":
            url = link.get("href", "")
            break
    abstract = re.sub(r"\s+", " ", (entry.findtext("a:summary", default="", namespaces=ATOM_NS) or "")).strip()
    return Paper(title, authors, year, abstract, url, "arxiv", 0)


def parse_openalex_work(work: dict) -> Paper:
    title = (work.get("title") or "").strip()
    year = work.get("publication_year") or 2000
    authors = tuple(
        a.get("author", {}).get("display_name", "")
        for a in work.get("authorships", [])[:20]
        if a.get("author") and a.get("author", {}).get("display_name")
    )
    url = work.get("doi") or work.get("id") or ""
    abstract_inv = work.get("abstract_inverted_index") or {}
    abstract = ""
    if isinstance(abstract_inv, dict) and abstract_inv:
        positions = [(i, w) for w, idxs in abstract_inv.items() if isinstance(idxs, list) for i in idxs]
        positions.sort()
        abstract = " ".join(w for _, w in positions)
    citation = work.get("cited_by_count") or 0
    if not isinstance(citation, int):
        citation = 0
    return Paper(title, authors, year, abstract, url, "openalex", citation)


def filter_and_rank(papers, q: Query) -> list:
    seen = set()
    out = []
    for p in papers:
        if not p.title:
            continue
        key = (p.title.lower().strip(), p.year)
        if key in seen:
            continue
        seen.add(key)
        if p.year < q.year_from:
            continue
        out.append(p)
    out.sort(key=lambda p: (-p.citation_count, -p.year, p.title.lower()))
    return out[: q.max_results]


def fetch_arxiv(q: Query) -> list:
    query = urllib.parse.urlencode({"search_query": build_arxiv_query(q), "start": 0, "max_results": q.max_results})
    url = f"{ARXIV_API}?{query}"
    with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    root = ET.fromstring(body)
    return [parse_arxiv_entry(e) for e in root.findall("a:entry", namespaces=ATOM_NS)]


def fetch_openalex(q: Query) -> list:
    query = urllib.parse.urlencode(
        {
            "search": " ".join(q.keywords),
            "filter": f"from_publication_date:{q.year_from}-01-01",
            "per-page": q.max_results,
            "select": "id,doi,title,publication_year,authorships,abstract_inverted_index,cited_by_count",
        }
    )
    url = f"{OPENALEX_API}?{query}"
    with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    data = json.loads(body)
    return [parse_openalex_work(w) for w in data.get("results", [])]


def run(raw: Any) -> dict:
    try:
        q = parse_query(raw)
    except ValueError as e:
        return {"ok": False, "error": "param_error", "message": str(e)}
    papers = []
    errors = []
    for name, fetch in (("arxiv", fetch_arxiv), ("openalex", fetch_openalex)):
        try:
            papers.extend(fetch(q))
        except Exception as e:
            errors.append(f"{name}: {type(e)}")
    if not papers and errors:
        return {"ok": False, "error": "network_error", "message": "检索失败: " + "; ".join(errors)}
    ranked = filter_and_rank(papers, q)
    return {"ok": True, "count": len(ranked), "papers": [p.to_dict() for p in ranked]}


if __name__ == "__main__":
    raw_input = sys.stdin.read().strip()
    if not raw_input:
        print(json.dumps({"ok": False, "error": "param_error", "message": "缺少输入 JSON"}, ensure_ascii=False))
        sys.exit(0)
    try:
        payload = json.loads(raw_input)
    except json.JSONDecodeError as e:
        print(json.dumps({"ok": False, "error": "param_error", "message": f"JSON 解析失败: {e}"}, ensure_ascii=False))
        sys.exit(0)
    print(json.dumps(run(payload), ensure_ascii=False))


def execute_output(params):
    """平台脚本节点入口：params.input 为上游 LLM 输出的 JSON 字符串，返回 JSON 字符串。"""
    raw = getattr(params, "input", None)
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            return json.dumps({"ok": False, "error": "param_error", "message": f"JSON 解析失败: {e}"}, ensure_ascii=False)
    else:
        payload = raw
    return json.dumps(run(payload), ensure_ascii=False)
