"""재료 챗봇 게이트웨이 — OpenAI 호환 /v1/chat/completions (docs/specs/2026-10-26-materials-chat-gateway-design.md)."""
import time

from fastapi import FastAPI

from app.auth import RateLimiter
from app.config import Settings


def create_app(settings: Settings, upstream=None, index=None, budget=None, clock=time.time) -> FastAPI:
    app = FastAPI(title="MAPS 재료 챗봇 게이트웨이", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.limiter = RateLimiter(settings.rate_per_hour, settings.rate_per_day, clock)

    @app.get("/health")
    def health():
        return {"ok": True}

    return app
