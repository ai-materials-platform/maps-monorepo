"""접속 코드 인증과 코드별 횟수 제한. 서버는 코드 원문이 아니라 SHA-256 해시만 가진다."""
import hashlib
import hmac
from collections import defaultdict, deque
from collections.abc import Callable


class AuthError(Exception):
    pass


class RateLimited(Exception):
    pass


def hash_code(code: str) -> str:
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def verify_code(authorization: str | None, hashes: frozenset[str]) -> str:
    scheme, _, code = (authorization or "").strip().partition(" ")
    if scheme.lower() != "bearer" or not code.strip():
        raise AuthError
    digest = hash_code(code)
    if not any(hmac.compare_digest(digest, h) for h in hashes):
        raise AuthError
    return digest


class RateLimiter:
    # ponytail: 메모리 보관 — 재시작하면 초기화, 인스턴스 여러 대면 각자 셈. 필요해지면 Redis 등으로
    def __init__(self, per_hour: int, per_day: int, clock: Callable[[], float]):
        self.per_hour, self.per_day, self.clock = per_hour, per_day, clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str) -> None:
        now = self.clock()
        hits = self._hits[key]
        while hits and now - hits[0] >= 86400:
            hits.popleft()
        last_hour = sum(1 for t in hits if now - t < 3600)
        if last_hour >= self.per_hour or len(hits) >= self.per_day:
            raise RateLimited
        hits.append(now)
