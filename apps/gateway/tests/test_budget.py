from datetime import UTC, datetime

import pytest

from app.budget import Budget, BudgetExceeded
from app.upstream import Usage
from conftest import FakeClock


def test_budget_records_and_resets_monthly():
    clock = FakeClock(datetime(2026, 10, 31, 23, tzinfo=UTC).timestamp())
    b = Budget(cap_usd=1.0, price_in_per_m=0.5, price_out_per_m=3.0, clock=clock)
    assert b.record(Usage(1_000_000, 100_000)) == pytest.approx(0.8)
    b.ensure_available()
    b.record(Usage(400_000, 0))  # 누적 1.0
    with pytest.raises(BudgetExceeded):
        b.ensure_available()
    clock.advance(3600 * 2)  # 11월로 넘어감
    b.ensure_available()
    assert b.spent() == 0
