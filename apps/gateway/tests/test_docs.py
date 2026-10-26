from pathlib import Path

from app.rag import parse_doc

DOCS = Path(__file__).resolve().parents[1] / "rag" / "docs"
REQUIRED = {"overview", "prediction-usage", "properties", "uncertainty", "charts", "simulation", "glossary"}


def test_required_maps_docs_exist():
    assert REQUIRED <= {p.stem for p in (DOCS / "maps").glob("*.md")}


def test_every_doc_has_front_matter_and_known_license():
    docs = [p for p in DOCS.rglob("*.md") if p.name != "SOURCES.md"]
    assert docs
    for p in docs:
        meta, body = parse_doc(p.read_text(encoding="utf-8"), str(p))
        assert body.strip(), p
        if "open" in p.parts:
            assert meta["source"].startswith("http") and meta["license"].lower() != "unknown", p


def test_open_docs_listed_in_sources():
    opens = list((DOCS / "open").glob("*.md"))
    assert opens, "공개 자료 문서가 하나도 없습니다"
    listed = (DOCS / "SOURCES.md").read_text(encoding="utf-8")
    for p in opens:
        assert parse_doc(p.read_text(encoding="utf-8"), str(p))[0]["source"] in listed, p
