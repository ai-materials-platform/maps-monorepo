"""테스트 공용 도구: 가짜 시계·가짜 업스트림·테스트 클라이언트. 실제 모델은 부르지 않는다."""
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import hash_code  # noqa: E402
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.rag import Index  # noqa: E402
from app.upstream import UpstreamError, Usage  # noqa: E402

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


class FakeUpstream:
    """replies: 문자열 목록(차례로, 마지막은 반복) 또는 messages를 받는 함수. 판정 모델 호출엔 guard_replies."""

    def __init__(self, replies=None, usage=Usage(10, 5), raise_error=False, guard_replies=None, embed_vector=None):
        self.replies = replies if replies is not None else ["답변"]
        self.usage = usage
        self.raise_error = raise_error
        self.guard_replies = list(guard_replies or ['{"allowed": true, "reason": "ok"}'])
        self.embed_vector = embed_vector or [1.0, 0.0]
        self.calls: list[dict] = []

    @staticmethod
    def _next(pool, messages):
        if callable(pool):
            return pool(messages)
        return pool.pop(0) if len(pool) > 1 else pool[0]

    def chat(self, model, messages, max_tokens, temperature):
        self.calls.append({"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature})
        if self.raise_error:
            raise UpstreamError(f"boom {SETTINGS.upstream_api_key}")
        pool = self.guard_replies if model == SETTINGS.guard_model else self.replies
        return self._next(pool, messages), self.usage

    def embed(self, model, texts):
        return [list(self.embed_vector) for _ in texts]


def make_client(upstream=None, index=None, clock=None, **overrides) -> TestClient:
    settings = dataclasses.replace(SETTINGS, **overrides)
    kwargs = {}
    if clock is not None:
        kwargs["clock"] = clock
    # 기본은 빈 색인 — 레포의 실제 rag/index.npz에 테스트가 묶이지 않게
    return TestClient(create_app(settings, upstream=upstream, index=index if index is not None else Index.empty(), **kwargs))
