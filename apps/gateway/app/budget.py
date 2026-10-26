"""월 사용액 상한. 토큰 사용량 × 단가로 센다."""
from collections.abc import Callable
from datetime import UTC, datetime

from app.upstream import Usage


class BudgetExceeded(Exception):
    pass


class Budget:
    # ponytail: 메모리 보관 — Render 재시작 시 0부터. 최종 안전장치는 DeepInfra 계정 사용액 한도 (스펙 8절)
    def __init__(self, cap_usd: float, price_in_per_m: float, price_out_per_m: float, clock: Callable[[], float]):
        self.cap, self.p_in, self.p_out, self.clock = cap_usd, price_in_per_m, price_out_per_m, clock
        self._month = None
        self._spent = 0.0

    def _roll(self) -> None:
        now = datetime.fromtimestamp(self.clock(), UTC)
        month = (now.year, now.month)
        if month != self._month:
            self._month, self._spent = month, 0.0

    def spent(self) -> float:
        self._roll()
        return self._spent

    def ensure_available(self) -> None:
        if self.spent() >= self.cap:
            raise BudgetExceeded

    def record(self, usage: Usage) -> float:
        self._roll()
        cost = usage.prompt_tokens / 1e6 * self.p_in + usage.completion_tokens / 1e6 * self.p_out
        self._spent += cost
        return cost
