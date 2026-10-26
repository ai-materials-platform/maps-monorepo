"""재료 챗봇 게이트웨이 — OpenAI 호환 /v1/chat/completions (docs/specs/2026-10-26-materials-chat-gateway-design.md)."""
import logging
import secrets
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.auth import AuthError, RateLimited, RateLimiter, verify_code
from app.budget import Budget, BudgetExceeded
from app.config import Settings
from app.guard import classify
from app.rag import Chunk, Index
from app.prompt import (
    REFUSAL_BUDGET, REFUSAL_LEAK, REFUSAL_OFF_TOPIC, build_messages, leaks_canary, make_system_prompt, split_messages, text_of,
)
from app.upstream import Upstream, UpstreamError, Usage

log = logging.getLogger("gateway")

ANSWER_MAX_TOKENS = 1024
ANSWER_TEMPERATURE = 0.3


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def _image_bytes(messages: list[dict]) -> int:
    total = 0
    for m in messages:
        if isinstance(m.get("content"), list):
            for p in m["content"]:
                if isinstance(p, dict) and p.get("type") == "image_url":
                    total += len(str((p.get("image_url") or {}).get("url", "")))
    return total


def _validate(body, settings: Settings) -> list[dict]:
    messages = body.get("messages") if isinstance(body, dict) else None
    if not isinstance(messages, list) or not messages or not all(isinstance(m, dict) for m in messages):
        raise ApiError(400, "bad_request", "messages 목록이 필요해요.")
    users = [m for m in messages if m.get("role") == "user"]
    if not users:
        raise ApiError(400, "bad_request", "사용자 질문이 없어요.")
    if len(text_of(users[-1].get("content"))) > settings.max_user_chars:
        raise ApiError(413, "too_large", f"질문은 {settings.max_user_chars}자 이내로 보내 주세요.")
    if _image_bytes(messages) > settings.max_image_bytes:
        raise ApiError(413, "too_large", "첨부 이미지가 너무 커요.")
    return messages


def _completion(settings: Settings, text: str, usage: Usage) -> dict:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": settings.llm_model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens,
                  "total_tokens": usage.prompt_tokens + usage.completion_tokens},
    }


RAG_DIR = Path(__file__).resolve().parents[1] / "rag"


def _load_default_index() -> Index:
    try:
        return Index.load(RAG_DIR)
    except FileNotFoundError:
        log.warning("RAG 색인(rag/index.npz)이 없어 자료 없이 답합니다. rag/build_index.py로 만드세요.")
        return Index.empty()


def create_app(settings: Settings, upstream: Upstream | None = None, index=None, budget: Budget | None = None,
               clock=time.time) -> FastAPI:
    app = FastAPI(title="MAPS 재료 챗봇 게이트웨이", docs_url=None, redoc_url=None, openapi_url=None)
    limiter = RateLimiter(settings.rate_per_hour, settings.rate_per_day, clock)
    budget = budget or Budget(settings.monthly_cap_usd, settings.price_in_per_m, settings.price_out_per_m, clock)
    canary = secrets.token_hex(8)  # 시스템 프롬프트 유출 탐지용 표식 (재시작마다 새로)
    system_prompt = make_system_prompt(canary)
    if upstream is None:
        from app.upstream import HttpUpstream  # noqa: PLC0415
        upstream = HttpUpstream(settings.upstream_base_url, settings.upstream_api_key)

    if index is None:
        index = _load_default_index()

    def _retrieve(question: str, tag: str) -> list[Chunk]:
        if not index.chunks:
            return []
        try:
            qvec = upstream.embed(settings.embed_model, [question])[0]
        except (UpstreamError, IndexError) as exc:  # 검색이 실패해도 답변은 자료 없이 계속
            log.warning("rag_error code=%s err=%s", tag, type(exc).__name__)
            return []
        return index.search(qvec, settings.rag_k, settings.rag_min_score)

    @app.exception_handler(ApiError)
    async def _api_error(_request: Request, exc: ApiError):
        return JSONResponse({"error": {"message": exc.message, "code": exc.code}}, status_code=exc.status)

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.post("/v1/chat/completions")
    async def chat(request: Request):
        try:
            who = verify_code(request.headers.get("authorization"), settings.access_code_hashes)
            limiter.hit(who)
        except AuthError:
            raise ApiError(401, "unauthorized", "접속 코드가 올바르지 않아요.") from None
        except RateLimited:
            raise ApiError(429, "rate_limited", "요청이 너무 많아요. 잠시 후 다시 시도해 주세요.") from None
        try:
            body = await request.json()
        except ValueError:
            raise ApiError(400, "bad_request", "JSON 본문이 필요해요.") from None
        messages = _validate(body, settings)
        tag = who[:8]

        try:
            budget.ensure_available()
        except BudgetExceeded:
            log.info("refused code=%s reason=budget", tag)
            return _completion(settings, REFUSAL_BUDGET, Usage(0, 0))

        app_context, turns = split_messages(messages)
        question = text_of(next(m for m in reversed(turns) if m["role"] == "user")["content"])
        try:
            verdict, guard_usage = classify(upstream, settings.guard_model, question)
            budget.record(guard_usage)
            if not verdict.allowed:
                log.info("refused code=%s reason=%s", tag, verdict.reason)
                return _completion(settings, REFUSAL_OFF_TOPIC, guard_usage)
            docs = _retrieve(question, tag)
            prompt = build_messages(system_prompt, docs, app_context, turns[-settings.max_turns:])
            text, usage = upstream.chat(settings.llm_model, prompt, ANSWER_MAX_TOKENS, ANSWER_TEMPERATURE)
        except UpstreamError as exc:
            log.warning("upstream_error code=%s err=%s", tag, type(exc).__name__)
            raise ApiError(502, "upstream_error", "답변 서버에 문제가 있어요. 잠시 후 다시 시도해 주세요.") from None
        cost = budget.record(usage)
        if leaks_canary(text, canary):
            log.warning("refused code=%s reason=leak", tag)
            return _completion(settings, REFUSAL_LEAK, usage)
        log.info("ok code=%s in=%d out=%d cost=%.5f", tag, usage.prompt_tokens, usage.completion_tokens, cost)
        return _completion(settings, text, usage)

    return app
