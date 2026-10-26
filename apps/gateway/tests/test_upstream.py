import json

import httpx

from app.config import load_settings
from app.upstream import HttpUpstream

ENV = {"UPSTREAM_BASE_URL": "https://u.invalid/v1", "UPSTREAM_API_KEY": "k", "LLM_MODEL": "m", "GUARD_MODEL": "g",
       "EMBED_MODEL": "e", "ACCESS_CODE_HASHES": "h", "PRICE_IN_PER_M": "0.1", "PRICE_OUT_PER_M": "0.95"}


def test_extra_body_setting_is_parsed():
    assert load_settings(ENV).upstream_extra_body == {}
    s = load_settings({**ENV, "UPSTREAM_EXTRA_BODY": '{"reasoning_effort": "none"}'})
    assert s.upstream_extra_body == {"reasoning_effort": "none"}


def test_http_upstream_merges_extra_body_into_chat_payload():
    seen = {}

    def handler(request: httpx.Request):
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "답"}}], "usage": {"prompt_tokens": 3, "completion_tokens": 1}})

    up = HttpUpstream("https://u.invalid/v1", "k", extra_body={"reasoning_effort": "none"}, transport=httpx.MockTransport(handler))
    text, usage = up.chat("m", [{"role": "user", "content": "q"}], 10, 0)
    assert (text, usage.prompt_tokens) == ("답", 3)
    assert seen["reasoning_effort"] == "none" and seen["model"] == "m"
