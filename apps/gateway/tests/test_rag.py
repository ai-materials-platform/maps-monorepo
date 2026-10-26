import numpy as np
import pytest

from app.rag import Chunk, Index, build, chunk_text, parse_doc
from conftest import AUTH, Q, URL, FakeUpstream, make_client

DOC = "---\ntitle: 용어집\nsource: maps/glossary.md\nlicense: team\n---\nFCC는 면심입방 구조다."


def test_chunk_text_respects_size_and_overlap():
    body = "\n\n".join(["가" * 300, "나" * 300, "다" * 300])
    parts = chunk_text(body, size=500, overlap=100)
    assert all(len(p) <= 500 for p in parts) and len(parts) >= 2
    assert parts[1].startswith(parts[0][-100:])
    assert chunk_text("짧은 글", size=500, overlap=100) == ["짧은 글"]
    assert all(len(p) <= 500 for p in chunk_text("라" * 1300, size=500, overlap=100))  # 문단 없는 긴 글


def test_parse_doc_requires_front_matter():
    meta, body = parse_doc(DOC, "g.md")
    assert meta == {"title": "용어집", "source": "maps/glossary.md", "license": "team"} and body == "FCC는 면심입방 구조다."
    with pytest.raises(ValueError, match="x.md"):
        parse_doc("# 제목만", "x.md")
    with pytest.raises(ValueError, match="y.md"):
        parse_doc("---\ntitle: t\nsource: s\n---\n본문", "y.md")  # license 없음


def test_search_orders_by_cosine_and_drops_low_scores():
    idx = Index(np.array([[1, 0], [0, 1], [0.7, 0.7]]), [Chunk("a", "s1", "t"), Chunk("b", "s2", "t"), Chunk("c", "s3", "t")])
    assert [c.text for c in idx.search([1, 0], k=2, min_score=0.3)] == ["a", "c"]
    assert idx.search([-1, 0], k=4, min_score=0.3) == []
    assert Index.empty().search([1, 0], k=4, min_score=0.0) == []


def test_index_save_load_roundtrip(tmp_path):
    idx = Index(np.array([[3.0, 4.0]]), [Chunk("a", "s", "t")])
    idx.save(tmp_path)
    loaded = Index.load(tmp_path)
    assert loaded.chunks == idx.chunks and loaded.search([3, 4], k=1, min_score=0.99)[0].text == "a"


def test_build_skips_sources_file_and_endpoint_injects_doc(tmp_path):
    (tmp_path / "g.md").write_text(DOC, encoding="utf-8")
    (tmp_path / "SOURCES.md").write_text("# 출처 목록", encoding="utf-8")
    idx = build(tmp_path, embed=lambda texts: [[1.0, 0.0] for _ in texts])
    assert [c.source for c in idx.chunks] == ["maps/glossary.md"]
    up = FakeUpstream(["답"], embed_vector=[1.0, 0.0])
    make_client(upstream=up, index=idx).post(URL, headers=AUTH, json=Q)
    assert '<자료 출처="maps/glossary.md">' in up.calls[-1]["messages"][0]["content"]


def test_unrelated_doc_is_not_injected(tmp_path):
    (tmp_path / "g.md").write_text(DOC, encoding="utf-8")
    idx = build(tmp_path, embed=lambda texts: [[0.0, 1.0] for _ in texts])
    up = FakeUpstream(["답"], embed_vector=[1.0, 0.0])
    make_client(upstream=up, index=idx).post(URL, headers=AUTH, json=Q)
    assert '<자료 출처="' not in up.calls[-1]["messages"][0]["content"]
