"""ModelEngine 불확실도가 실제 오차 크기에 맞게 보정되는지 확인한다.

앙상블 편차만 쓰면 TFP는 과신한다 (실데이터 ±2σ 포함률 71~77%, 연신율 ±0.8%).
검증 세트로 출력별 σ' = a + b·σ를 맞추면 노이즈 수준만큼 σ가 나온다.

실행: python apps/prediction/src/engine/test_model_engine_noise.py
"""
import os
import sys
import tempfile

import joblib
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.engine.model_engine import ModelEngine  # noqa: E402

NOISE = 0.5


def make_data(n, seed):
    rng = np.random.default_rng(seed)
    X = rng.uniform(-1, 1, size=(n, 3))
    y = np.column_stack([X[:, 0] + X[:, 1], X[:, 2] * 2]) + rng.normal(0, NOISE, size=(n, 2))
    return X.astype(np.float32), y


def test_std_reflects_data_noise():
    X, y = make_data(1200, 0)
    Xv, yv = make_data(300, 1)
    for kind in ("TFP", "RF"):
        m = ModelEngine(kind, output_dim=2, max_iter=300)
        m.train(X, y, X_val=Xv, y_val=yv)
        _, std = m.predict(Xv[:50])
        # 실제 노이즈 0.5 → 보정된 σ가 그 근처여야 한다 (앙상블 편차만이면 훨씬 작음)
        assert 0.6 * NOISE < np.median(std) < 1.6 * NOISE, f"{kind}: median std {np.median(std):.3f} vs noise {NOISE}"


def test_noise_survives_save_load_and_old_files_still_load():
    X, y = make_data(400, 2)
    Xv, yv = make_data(100, 3)
    m = ModelEngine("RF", output_dim=2)
    m.train(X, y, X_val=Xv, y_val=yv)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "m.pkl")
        m.save(p)
        m2 = ModelEngine(output_dim=2)
        m2.load(p)
        assert np.allclose(m2.std_affine, m.std_affine)
        assert (m.std_affine >= 0).all(), "a, b는 음수가 될 수 없다"
        # 기존 저장 형식(보정값 없음)도 그대로 로드 → 예전처럼 앙상블 편차만
        joblib.dump({"model": m.model, "type": "RF"}, p)
        m3 = ModelEngine(output_dim=2)
        m3.load(p)
        assert m3.std_affine is None
        m3.predict(Xv[:5])
        # #11 형식(계수만, std_scale)은 a=0, b=계수로 읽는다
        joblib.dump({"model": m.model, "type": "RF", "std_scale": np.array([2.0, 3.0])}, p)
        m4 = ModelEngine(output_dim=2)
        m4.load(p)
        _, raw = m4._predict_raw(Xv[:5])
        _, cal = m4.predict(Xv[:5])
        assert np.allclose(cal, raw * np.array([2.0, 3.0]))


if __name__ == "__main__":
    test_std_reflects_data_noise()
    test_noise_survives_save_load_and_old_files_still_load()
    print("ok - model uncertainty calibrated to data noise")
