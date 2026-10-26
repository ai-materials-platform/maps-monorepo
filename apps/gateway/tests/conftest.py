"""테스트 공용 도구: 가짜 시계·가짜 업스트림·테스트 클라이언트. 실제 모델은 부르지 않는다."""
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import hash_code  # noqa: E402
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

CODE = "test-code"
AUTH = {"Authorization": f"Bearer {CODE}"}
URL = "/v1/chat/completions"
Q = {"messages": [{"role": "user", "content": "오스테나이트계 스테인리스강의 특징은?"}]}

SETTINGS = Settings(
    upstream_base_url="https://upstream.invalid/v1",
    upstream_api_key="sk-secret-upstream-key",
    llm_model="answer-model",
    guard_model="guard-model",
    embed_model="embed-model",
    access_code_hashes=frozenset({hash_code(CODE)}),
    price_in_per_m=0.5,
    price_out_per_m=3.0,
)


class FakeClock:
    def __init__(self, t: float = 0.0):
        self.t = float(t)

    def __call__(self) -> float:
        return self.t

    def advance(self, sec: float) -> None:
        self.t += sec


def make_client(upstream=None, index=None, clock=None, **overrides) -> TestClient:
    settings = dataclasses.replace(SETTINGS, **overrides)
    kwargs = {}
    if clock is not None:
        kwargs["clock"] = clock
    return TestClient(create_app(settings, upstream=upstream, index=index, **kwargs))
