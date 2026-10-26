import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.auth import hash_code, verify_code

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from new_code import new_code  # noqa: E402


def test_new_code_hash_matches_gateway_hash():
    code, h = new_code()
    assert len(code) >= 20 and h == hash_code(code)
    assert verify_code(f"Bearer {code}", frozenset({h})) == h
    assert new_code()[0] != code


def test_app_from_env_builds_app(monkeypatch):
    from app.main import app_from_env

    for k, v in {
        "UPSTREAM_BASE_URL": "https://u.invalid/v1", "UPSTREAM_API_KEY": "k", "LLM_MODEL": "m", "GUARD_MODEL": "g",
        "EMBED_MODEL": "e", "ACCESS_CODE_HASHES": hash_code("c"), "PRICE_IN_PER_M": "0.5", "PRICE_OUT_PER_M": "3",
    }.items():
        monkeypatch.setenv(k, v)
    assert TestClient(app_from_env()).get("/health").json() == {"ok": True}
