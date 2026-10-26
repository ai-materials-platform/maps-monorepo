"""업스트림(DeepInfra 등 OpenAI 호환) 호출. 테스트는 같은 모양의 가짜를 주입한다."""
from dataclasses import dataclass
from typing import Protocol

import httpx


class UpstreamError(Exception):
    """업스트림 실패. 메시지는 로그용 — 사용자 응답에 그대로 내보내지 않는다."""


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int


class Upstream(Protocol):
    def chat(self, model: str, messages: list[dict], max_tokens: int, temperature: float) -> tuple[str, Usage]: ...

    def embed(self, model: str, texts: list[str]) -> list[list[float]]: ...


class HttpUpstream:
    def __init__(self, base_url: str, api_key: str, timeout: float = 60.0, extra_body: dict | None = None,
                 transport: httpx.BaseTransport | None = None):
        self._extra = dict(extra_body or {})
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout, transport=transport,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )

    def _post(self, path: str, payload: dict) -> dict:
        last: Exception | None = None
        for _ in range(2):  # 1회 재시도
            try:
                r = self._client.post(path, json=payload)
                if r.status_code < 500:
                    r.raise_for_status()
                    return r.json()
                last = UpstreamError(f"{path} HTTP {r.status_code}")
            except (httpx.HTTPError, ValueError) as exc:
                last = exc
        raise UpstreamError(f"{path} 실패: {type(last).__name__}")

    def chat(self, model, messages, max_tokens, temperature):
        data = self._post("/chat/completions", {
            **self._extra, "model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature,
        })
        try:
            text = data["choices"][0]["message"]["content"] or ""
            u = data.get("usage") or {}
            return text, Usage(int(u.get("prompt_tokens", 0)), int(u.get("completion_tokens", 0)))
        except (KeyError, IndexError, TypeError) as exc:
            raise UpstreamError("chat 응답 형식 오류") from exc

    def embed(self, model, texts):
        data = self._post("/embeddings", {"model": model, "input": texts})
        try:
            return [item["embedding"] for item in sorted(data["data"], key=lambda d: d["index"])]
        except (KeyError, TypeError) as exc:
            raise UpstreamError("embedding 응답 형식 오류") from exc
