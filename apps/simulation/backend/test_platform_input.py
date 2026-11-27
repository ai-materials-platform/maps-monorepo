"""build_platform_input 기본값이 학습 데이터 범위 안인지 확인한다.

범위 밖 기본값(결정립 12000, 잉곳 100, 용체화 1050K)이 들어가면 MLP 앙상블(TFP)이
제각각 외삽해 UTS ±1000MPa 같은 불확실도가 나온다.
범위는 STMECH_AUS_SS.xls 학습 데이터의 min~max.

실행: python apps/simulation/backend/test_platform_input.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from simulation_server import build_platform_input, elastic_modulus_gpa, find_out_of_range  # noqa: E402

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


def test_out_of_range_flags_only_inputs_outside_training_data():
    ranges = {"Cr": (16.0, 21.06), "Ni": (8.4, 34.45), "Al": (0.0, 0.52), "Temperature (K)": (293.0, 1273.0)}
    inside = build_platform_input({"Cr": 18, "Ni": 10})
    assert find_out_of_range(inside, ranges) == []
    outside = find_out_of_range(build_platform_input({"Ni": 42, "Ti": 31, "Cr": 27}), ranges)
    assert [item["key"] for item in outside] == ["Cr", "Ni"], outside
    assert outside[1] == {"key": "Ni", "value": 42.0, "min": 8.4, "max": 34.45}
    # 범위 폭의 2%까지는 경고하지 않는다 (Cr 21.1은 21.06 바로 위)
    assert find_out_of_range(build_platform_input({"Cr": 21.1, "Ni": 10}), ranges) == []


def test_elastic_modulus_follows_austenitic_table():
    assert elastic_modulus_gpa(293.15) == 195            # 상온 오스테나이트계 약 195 GPa
    assert elastic_modulus_gpa(250) == 195               # 표 아래쪽은 끝값
    assert abs(elastic_modulus_gpa(273.15 + 450) - 163) < 1e-9   # 400 °C 167과 500 °C 159 사이
    assert elastic_modulus_gpa(2000) == 120              # 표 위쪽은 끝값


if __name__ == "__main__":
    test_defaults_inside_training_range()
    test_out_of_range_flags_only_inputs_outside_training_data()
    test_elastic_modulus_follows_austenitic_table()
    print("ok - platform input defaults inside training range")
