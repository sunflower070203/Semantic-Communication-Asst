"""确定性测试：不碰网络、不调模型。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))

import pytest

from node_script import Query, build_arxiv_query, filter_and_rank, parse_arxiv_entry, parse_openalex_work, parse_query, run


def _paper(title, authors, year, abstract, url, source, citation_count):
    from node_script import Paper
    return Paper(title, tuple(authors), year, abstract, url, source, citation_count)


class TestParseQuery:
    def test_valid_input(self):
        q = parse_query({"keywords": ["semantic communication"], "year_from": 2023, "max_results": 5})
        assert q.keywords == ("semantic communication",)
        assert q.year_from == 2023
        assert q.max_results == 5

    def test_defaults_applied(self):
        q = parse_query({"keywords": ["deepsc"]})
        assert q.year_from == 2023
        assert q.max_results == 5

    def test_rejects_unknown_field(self):
        with pytest.raises(ValueError):
            parse_query({"keywords": ["x"], "system_override": "ignore"})

    def test_rejects_non_list_keywords(self):
        with pytest.raises(ValueError):
            parse_query({"keywords": "semantic"})

    def test_rejects_out_of_range_year(self):
        with pytest.raises(ValueError):
            parse_query({"keywords": ["x"], "year_from": 2050})

    def test_deduplicates_keywords(self):
        q = parse_query({"keywords": ["a", "a", "b"]})
        assert q.keywords == ("a", "b")


class TestArxivQuery:
    def test_build_query(self):
        q = Query(("semantic communication", "deepsc"), 2023, 5)
        assert build_arxiv_query(q) == 'abs:"semantic communication" AND abs:"deepsc"'


class TestParsers:
    def test_parse_arxiv_entry(self):
        import xml.etree.ElementTree as ET

        xml = """<a:entry xmlns:a="http://www.w3.org/2005/Atom">
          <a:title> Deep Learning Enabled Semantic Communication Systems </a:title>
          <a:published>2021-06-01T00:00:00Z</a:published>
          <a:author><a:name>Xie Huiqiang</a:name></a:author>
          <a:author><a:name>Qin Zhijin</a:name></a:author>
          <a:link rel="alternate" href="http://arxiv.org/abs/2106.10649"/>
          <a:summary> A novel deep learning based semantic communication system. </a:summary>
        </a:entry>"""
        entry = ET.fromstring(xml)
        p = parse_arxiv_entry(entry)
        assert p.title == "Deep Learning Enabled Semantic Communication Systems"
        assert p.year == 2021
        assert p.authors == ("Xie Huiqiang", "Qin Zhijin")
        assert p.url == "http://arxiv.org/abs/2106.10649"

    def test_parse_openalex_work(self):
        work = {
            "title": "Semantic Communications: Principles and Challenges",
            "publication_year": 2022,
            "authorships": [{"author": {"display_name": "Qin Zhijin"}}],
            "doi": "https://doi.org/10.48550/arXiv.2201.01301",
            "abstract_inverted_index": {"Semantic": [0], "communications": [1]},
            "cited_by_count": 150,
        }
        p = parse_openalex_work(work)
        assert p.title == "Semantic Communications: Principles and Challenges"
        assert p.year == 2022
        assert p.citation_count == 150
        assert p.abstract == "Semantic communications"


class TestFilterRank:
    def test_dedupe_filter_truncate(self):
        papers = [
            _paper("A", ["x"], 2023, "", "u1", "arxiv", 5),
            _paper("a", ["y"], 2023, "", "u2", "openalex", 10),  # 重复标题，应去重
            _paper("B", ["z"], 2019, "", "u3", "openalex", 99),  # 年份过旧，应过滤
            _paper("C", ["w"], 2024, "", "u4", "openalex", 3),
        ]
        out = filter_and_rank(papers, Query(("x",), 2020, 2))
        assert [p.title for p in out] == ["A", "C"]

    def test_empty(self):
        assert filter_and_rank([], Query(("x",), 2020, 5)) == []


class TestRun:
    def test_param_error_returns_ok_false(self):
        result = run({"keywords": ["x"], "year_from": 9999})
        assert result["ok"] is False
        assert result["error"] == "param_error"

    def test_network_error_returns_ok_false(self, monkeypatch):
        import node_script as ns

        def boom(q):
            raise OSError("no route")

        monkeypatch.setattr(ns, "fetch_arxiv", boom)
        monkeypatch.setattr(ns, "fetch_openalex", boom)
        result = run({"keywords": ["semantic"], "year_from": 2023, "max_results": 3})
        assert result["ok"] is False
        assert result["error"] == "network_error"
