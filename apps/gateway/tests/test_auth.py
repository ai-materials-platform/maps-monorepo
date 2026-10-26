import pytest

from app.auth import AuthError, RateLimited, RateLimiter, hash_code, verify_code
from app.config import load_settings
from conftest import FakeClock, make_client


def test_hash_strips_whitespace():
    assert hash_code("  abc\n") == hash_code("abc")


def test_verify_code_accepts_bearer_and_rejects_others():
    hs = frozenset({hash_code("good")})
    assert verify_code("Bearer good", hs) == hash_code("good")
    assert verify_code("Bearer  good \n", hs) == hash_code("good")
    for bad in (None, "", "Bearer bad", "good", "Basic good", "Bearer "):
        with pytest.raises(AuthError):
            verify_code(bad, hs)


def test_rate_limiter_hour_and_day_windows():
    clock = FakeClock(0)
    rl = RateLimiter(per_hour=2, per_day=3, clock=clock)
    rl.hit("k")
    rl.hit("k")
    with pytest.raises(RateLimited):
        rl.hit("k")
    clock.advance(3601)
    rl.hit("k")  # 시간 창이 풀림
    with pytest.raises(RateLimited):
        rl.hit("k")  # 하루 3회 초과
    clock.advance(86401)
    rl.hit("k")
    rl.hit("other")  # 키별 독립


def test_health_and_missing_setting():
    assert make_client().get("/health").json() == {"ok": True}
    with pytest.raises(ValueError, match="UPSTREAM_API_KEY"):
        load_settings({"UPSTREAM_BASE_URL": "x"})
