"""rag/docs/**/*.md → rag/index.npz + rag/chunks.json (임베딩 모델 호출, 비용 몇 센트).

실행: cd apps/gateway && python rag/build_index.py
필요한 환경변수: UPSTREAM_BASE_URL, UPSTREAM_API_KEY, EMBED_MODEL
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.rag import build  # noqa: E402
from app.upstream import HttpUpstream  # noqa: E402


def main() -> None:
    missing = [k for k in ("UPSTREAM_BASE_URL", "UPSTREAM_API_KEY", "EMBED_MODEL") if not os.environ.get(k)]
    if missing:
        sys.exit(f"환경변수가 없습니다: {', '.join(missing)}")
    up = HttpUpstream(os.environ["UPSTREAM_BASE_URL"], os.environ["UPSTREAM_API_KEY"])
    index = build(ROOT / "rag" / "docs", embed=lambda texts: up.embed(os.environ["EMBED_MODEL"], texts))
    index.save(ROOT / "rag")
    print(f"ok - {len(index.chunks)} chunks from {len({c.source for c in index.chunks})} docs")


if __name__ == "__main__":
    main()
