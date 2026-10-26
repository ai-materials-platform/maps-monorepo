import json
import sys
from collections import Counter
from pathlib import Path

from app.prompt import REFUSAL_BUDGET, REFUSAL_OFF_TOPIC

EVAL = Path(__file__).resolve().parents[1] / "eval"
sys.path.insert(0, str(EVAL))
from run_eval import is_refusal, summarize  # noqa: E402

KINDS = {"role_override", "ignore_rules", "prompt_leak", "off_topic", "encoding", "multilingual", "fake_context", "jailbreak_story"}


def _load(name):
    return [json.loads(line) for line in (EVAL / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def test_eval_sets_have_required_coverage():
    attacks, normal = _load("attacks.jsonl"), _load("normal.jsonl")
    assert len(attacks) >= 40 and len(normal) >= 40
    kinds = Counter(a["kind"] for a in attacks)
    assert set(kinds) <= KINDS and all(kinds[k] >= 3 for k in KINDS), kinds
    assert all(a.get("system") for a in attacks if a["kind"] == "fake_context")
    topics = Counter(n["topic"] for n in normal)
    assert set(topics) == {"materials", "maps"} and min(topics.values()) >= 15, topics
    assert len({a["q"] for a in attacks}) == len(attacks) and len({n["q"] for n in normal}) == len(normal)


def test_summarize_applies_thresholds():
    rows = [{"set": "attack", "refused": True}] * 19 + [{"set": "attack", "refused": False}] + [{"set": "normal", "refused": False}] * 20
    s = summarize(rows)
    assert (s["blocked"], s["attacks"], s["refused"], s["normal"], s["passed"]) == (19, 20, 0, 20, True)  # 95%, 0%
    rows[-1] = {"set": "normal", "refused": True}
    rows[-2] = {"set": "normal", "refused": True}
    assert summarize(rows)["passed"] is False  # 잘못 거절 10%


def test_is_refusal():
    assert is_refusal(REFUSAL_OFF_TOPIC) and is_refusal("  " + REFUSAL_OFF_TOPIC + " 추가")
    assert not is_refusal(REFUSAL_BUDGET)  # 한도 거절은 판정 거절과 따로 센다
    assert not is_refusal("FCC는 면심입방 구조입니다.")
