from app.prompt import REFUSAL_BUDGET
from conftest import AUTH, Q, SETTINGS, URL, FakeUpstream, make_client


def test_chat_returns_openai_shape_and_ignores_client_model():
    up = FakeUpstream(["답"])
    c = make_client(upstream=up)
    r = c.post(URL, headers=AUTH, json={"model": "gpt-4o-mini", **Q})
    body = r.json()
    assert r.status_code == 200
    assert body["object"] == "chat.completion" and body["model"] == SETTINGS.llm_model
    assert body["choices"][0]["message"] == {"role": "assistant", "content": "답"}
    assert up.calls[-1]["model"] == SETTINGS.llm_model


def test_auth_rate_and_size_errors_are_openai_shaped():
    c = make_client(upstream=FakeUpstream(), rate_per_hour=1)
    r = c.post(URL, json=Q)
    assert (r.status_code, r.json()["error"]["code"]) == (401, "unauthorized")
    assert c.post(URL, headers=AUTH, json=Q).status_code == 200
    r = c.post(URL, headers=AUTH, json=Q)
    assert (r.status_code, r.json()["error"]["code"]) == (429, "rate_limited")

    long = {"messages": [{"role": "user", "content": "가" * 2001}]}
    r = make_client(upstream=FakeUpstream()).post(URL, headers=AUTH, json=long)
    assert (r.status_code, r.json()["error"]["code"]) == (413, "too_large")
    img = {"type": "image_url", "image_url": {"url": "data:image/png;base64," + "A" * 7_000_000}}
    big = {"messages": [{"role": "user", "content": [{"type": "text", "text": "그래프 봐줘"}, img]}]}
    assert make_client(upstream=FakeUpstream()).post(URL, headers=AUTH, json=big).status_code == 413

    for bad in ({}, {"messages": []}, {"messages": [{"role": "assistant", "content": "x"}]}, {"messages": "x"}):
        r = make_client(upstream=FakeUpstream()).post(URL, headers=AUTH, json=bad)
        assert (r.status_code, r.json()["error"]["code"]) == (400, "bad_request"), bad


def test_upstream_failure_is_502_without_secrets():
    r = make_client(upstream=FakeUpstream(raise_error=True)).post(URL, headers=AUTH, json=Q)
    assert (r.status_code, r.json()["error"]["code"]) == (502, "upstream_error")
    assert SETTINGS.upstream_api_key not in r.text and "Traceback" not in r.text


def test_only_recent_turns_are_forwarded():
    up = FakeUpstream(["ok"])
    msgs = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(21)]
    make_client(upstream=up).post(URL, headers=AUTH, json={"messages": msgs})
    sent = [m for m in up.calls[-1]["messages"] if m["role"] in ("user", "assistant")]
    assert len(sent) <= 8 and sent[-1]["content"] == "m20"


def test_budget_exceeded_returns_refusal_text():
    up = FakeUpstream()
    r = make_client(upstream=up, monthly_cap_usd=0.0).post(URL, headers=AUTH, json=Q)
    assert r.status_code == 200 and r.json()["choices"][0]["message"]["content"] == REFUSAL_BUDGET
    assert up.calls == []


def test_total_context_size_is_limited():
    # 마지막 질문만 짧고 이전 턴·앱상태가 거대하면 토큰(비용)이 폭증한다 → 전체 글자 수도 제한
    up = FakeUpstream()
    big_history = {"messages": [{"role": "user", "content": "가" * 1900}, {"role": "assistant", "content": "나" * 1900}] * 4
                   + [{"role": "user", "content": "q"}]}
    r = make_client(upstream=up).post(URL, headers=AUTH, json=big_history)
    assert (r.status_code, r.json()["error"]["code"]) == (413, "too_large") and up.calls == []
    big_ctx = {"messages": [{"role": "system", "content": "x" * 20_000}, {"role": "user", "content": "q"}]}
    assert make_client(upstream=FakeUpstream()).post(URL, headers=AUTH, json=big_ctx).status_code == 413
    ok = {"messages": [{"role": "system", "content": "예측 결과 " * 200}, {"role": "user", "content": "q"}]}
    assert make_client(upstream=FakeUpstream()).post(URL, headers=AUTH, json=ok).status_code == 200
