"""게이트웨이 설정 — 전부 환경변수(Render)에서 읽는다. 모델 ID·단가도 코드에 박지 않는다."""
import json
from collections.abc import Mapping
from dataclasses import dataclass, field

REQUIRED = (
    "UPSTREAM_BASE_URL", "UPSTREAM_API_KEY", "LLM_MODEL", "GUARD_MODEL", "EMBED_MODEL",
    "ACCESS_CODE_HASHES", "PRICE_IN_PER_M", "PRICE_OUT_PER_M",
)


@dataclass(frozen=True)
class Settings:
    upstream_base_url: str
    upstream_api_key: str
    llm_model: str
    guard_model: str
    embed_model: str
    access_code_hashes: frozenset[str]
    price_in_per_m: float
    price_out_per_m: float
    rate_per_hour: int = 30
    rate_per_day: int = 200
    monthly_cap_usd: float = 10.0
    max_user_chars: int = 2000
    max_turns: int = 8
    max_image_bytes: int = 5_000_000
    rag_k: int = 4
    rag_min_score: float = 0.3
    # 업스트림 chat 요청에 덧붙일 필드 (예: 생각 모드 끄기 {"reasoning_effort": "none"})
    upstream_extra_body: dict = field(default_factory=dict)


def load_settings(env: Mapping[str, str]) -> Settings:
    missing = [k for k in REQUIRED if not env.get(k, "").strip()]
    if missing:
        raise ValueError(f"필수 환경변수가 없습니다: {', '.join(missing)}")
    num = lambda key, default, cast: cast(env[key]) if env.get(key, "").strip() else default  # noqa: E731
    return Settings(
        upstream_base_url=env["UPSTREAM_BASE_URL"].strip().rstrip("/"),
        upstream_api_key=env["UPSTREAM_API_KEY"].strip(),
        llm_model=env["LLM_MODEL"].strip(),
        guard_model=env["GUARD_MODEL"].strip(),
        embed_model=env["EMBED_MODEL"].strip(),
        access_code_hashes=frozenset(h.strip().lower() for h in env["ACCESS_CODE_HASHES"].split(",") if h.strip()),
        price_in_per_m=float(env["PRICE_IN_PER_M"]),
        price_out_per_m=float(env["PRICE_OUT_PER_M"]),
        rate_per_hour=num("RATE_PER_HOUR", 30, int),
        rate_per_day=num("RATE_PER_DAY", 200, int),
        monthly_cap_usd=num("MONTHLY_CAP_USD", 10.0, float),
        upstream_extra_body=json.loads(env.get("UPSTREAM_EXTRA_BODY") or "{}"),
    )
