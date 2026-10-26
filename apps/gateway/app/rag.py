"""RAG: 문서 조각 나누기, 색인 저장·불러오기, 코사인 유사도 검색. 규모가 작아 메모리에서 numpy로 충분하다."""
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

REQUIRED_META = ("title", "source", "license")
SKIP_FILES = {"SOURCES.md"}


@dataclass(frozen=True)
class Chunk:
    text: str
    source: str
    title: str


def parse_doc(text: str, path: str) -> tuple[dict, str]:
    """맨 앞 '---' 블록의 key: value 머리와 본문. title/source/license가 다 있어야 한다."""
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---" or "---" not in (l.strip() for l in lines[1:]):
        raise ValueError(f"{path}: 문서 머리(---)가 없습니다")
    end = next(i for i, l in enumerate(lines[1:], 1) if l.strip() == "---")
    meta = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip()
    missing = [k for k in REQUIRED_META if not meta.get(k)]
    if missing:
        raise ValueError(f"{path}: 문서 머리에 {', '.join(missing)} 가 없습니다")
    return {k: meta[k] for k in REQUIRED_META}, "\n".join(lines[end + 1:]).strip()


def chunk_text(body: str, size: int = 500, overlap: int = 100) -> list[str]:
    """문단 경계를 우선해 (size - overlap)자 이하 조각으로 묶고, 앞 조각 끝 overlap자를 다음 조각 앞에 붙인다."""
    step = size - overlap
    paras = [p.strip() for p in body.split("\n\n") if p.strip()]
    slices = [p[i:i + step] for p in paras for i in range(0, len(p), step)]
    pieces: list[str] = []
    for s in slices:
        if pieces and len(pieces[-1]) + 2 + len(s) <= step:
            pieces[-1] += "\n\n" + s
        else:
            pieces.append(s)
    return [p if i == 0 else pieces[i - 1][-overlap:] + p for i, p in enumerate(pieces)]


class Index:
    def __init__(self, vectors, chunks: list[Chunk]):
        v = np.asarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(v, axis=1, keepdims=True) if v.size else np.ones((0, 1), np.float32)
        self.vectors = v / np.where(norms == 0, 1, norms)
        self.chunks = list(chunks)

    @classmethod
    def empty(cls) -> "Index":
        return cls(np.zeros((0, 0), np.float32), [])

    def search(self, qvec, k: int, min_score: float) -> list[Chunk]:
        if not self.chunks:
            return []
        q = np.asarray(qvec, dtype=np.float32)
        q = q / (np.linalg.norm(q) or 1)
        scores = self.vectors @ q
        order = np.argsort(-scores)[:k]
        return [self.chunks[i] for i in order if scores[i] >= min_score]

    def save(self, directory: Path) -> None:
        directory = Path(directory)
        np.savez(directory / "index.npz", vectors=self.vectors)
        (directory / "chunks.json").write_text(
            json.dumps([asdict(c) for c in self.chunks], ensure_ascii=False, indent=0), encoding="utf-8")

    @classmethod
    def load(cls, directory: Path) -> "Index":
        directory = Path(directory)
        vectors = np.load(directory / "index.npz")["vectors"]
        chunks = [Chunk(**c) for c in json.loads((directory / "chunks.json").read_text(encoding="utf-8"))]
        return cls(vectors, chunks)


def build(docs_dir: Path, embed: Callable[[list[str]], list[list[float]]], size: int = 500,
          overlap: int = 100, batch: int = 32) -> Index:
    chunks: list[Chunk] = []
    for path in sorted(Path(docs_dir).rglob("*.md")):
        if path.name in SKIP_FILES:
            continue
        meta, body = parse_doc(path.read_text(encoding="utf-8"), str(path))
        chunks += [Chunk(t, meta["source"], meta["title"]) for t in chunk_text(body, size, overlap)]
    vectors: list[list[float]] = []
    for i in range(0, len(chunks), batch):
        vectors += embed([c.text for c in chunks[i:i + batch]])
    return Index(np.array(vectors, dtype=np.float32) if vectors else np.zeros((0, 0), np.float32), chunks)
