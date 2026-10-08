"""build_platform_input 기본값이 학습 데이터 범위 안인지 확인한다.

범위 밖 기본값(결정립 12000, 잉곳 100, 용체화 1050K)이 들어가면 MLP 앙상블(TFP)이
제각각 외삽해 UTS ±1000MPa 같은 불확실도가 나온다.
범위는 STMECH_AUS_SS.xls 학습 데이터의 min~max.

실행: python apps/simulation/backend/test_platform_input.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from simulation_server import build_platform_input  # noqa: E402

TRAIN_RANGE = {
    "Solution_treatment_temperature": (1279, 1473),  # K
    "Grains mm-2": (37, 1024),
    "Size of ingot": (0.21, 16),
    "Temperature (K)": (293, 1273),
}


def test_defaults_inside_training_range():
    x = build_platform_input({"Ni": 10, "Cr": 18})
    for key, (lo, hi) in TRAIN_RANGE.items():
        assert lo <= x[key] <= hi, f"{key}={x[key]} outside training range {lo}~{hi}"


if __name__ == "__main__":
    test_defaults_inside_training_range()
    print("ok - platform input defaults inside training range")
