"""/domain 이 사전학습 데이터 범위를 /predict 키 이름 그대로 돌려주는지 확인한다.

실행: python apps/prediction/src/api/test_domain.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.api.server import TARGET_NAMES, app  # noqa: E402


def test_domain():
    res = app.test_client().get("/domain")
    assert res.status_code == 200, res.get_json()
    body = res.get_json()
    assert body["samples"] > 0
    assert sorted(body["targets"]) == sorted(TARGET_NAMES), list(body["targets"])
    for r in [*body["features"].values(), *body["targets"].values()]:
        assert r["min"] <= r["median"] <= r["max"]
    fe = body["features"]["Fe"]
    assert fe["min"] > 0  # 미지정=0 은 범위 밖 → median 기본값이 필요한 이유


if __name__ == "__main__":
    test_domain()
    print("ok")
