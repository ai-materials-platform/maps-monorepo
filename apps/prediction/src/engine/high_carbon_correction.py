"""고탄소 영역 연신율 보정 (SAE as-rolled 실측 추세 기반).

배경
----
사전학습 RF 모델은 오스테나이트 스테인리스 분포로 학습되어 C/Ni 변화에
둔감하다. 고C 영역에서는 모델 연신율이 과대평가되므로, SAE 탄소강
as-rolled 실측(A5 vs C)으로부터 상대계수 f(C)를 구해 연신율에만 곱한다.
강도(YS/UTS)는 모델값을 그대로 둔다 (이중 계산 방지).

실측 (출처: Kaggle 'Materials and their Mechanical Properties', SAE as-rolled)
    C%:    0.15  0.20  0.22  0.30  0.40  0.50  0.60  0.80  0.95
    A5%:   39.0  36.0  35.0  32.0  25.0  20.0  17.0  12.0   9.0

규칙
----
- C <= 0.15%: 보정 없음 (학습 분포 안).
- 0.15% < C <= 0.95%: A5 실측比 선형 보간.
- 0.95% < C <= 2.0%: 로그-선형 외삽, 하한 0.08. 결과에 '외삽' 명시.
- C > 2.0%: 보정 거부 (범위 초과). 모델값 그대로 + 경고 정보 반환.
"""

import math

# (C wt%, A5 %) 실측 점
_A5_POINTS = (
    (0.15, 39.0),
    (0.20, 36.0),
    (0.22, 35.0),
    (0.30, 32.0),
    (0.40, 25.0),
    (0.50, 20.0),
    (0.60, 17.0),
    (0.80, 12.0),
    (0.95, 9.0),
)

_BASE_C, _BASE_A5 = _A5_POINTS[0]
_MAX_MEASURED_C = _A5_POINTS[-1][0]
_REFUSE_ABOVE_C = 2.0
_MIN_FACTOR = 0.08


def _interp_a5(c):
    pts = _A5_POINTS
    if c <= pts[0][0]:
        return pts[0][1]
    for (c0, a0), (c1, a1) in zip(pts, pts[1:]):
        if c <= c1:
            t = (c - c0) / (c1 - c0)
            return a0 + t * (a1 - a0)
    return pts[-1][1]


def elongation_factor(c_pct):
    """C 함량(wt%) → 연신율 상대계수 f. (factor, extrapolated, refused) 반환."""
    try:
        c = float(c_pct)
    except (TypeError, ValueError):
        return 1.0, False, False
    if not math.isfinite(c) or c <= _BASE_C:
        return 1.0, False, False
    if c > _REFUSE_ABOVE_C:
        return 1.0, False, True
    if c <= _MAX_MEASURED_C:
        return max(_interp_a5(c) / _BASE_A5, _MIN_FACTOR), False, False
    # 로그-선형 외삽: 마지막 두 점의 기울기 사용
    (c0, a0), (c1, a1) = _A5_POINTS[-2], _A5_POINTS[-1]
    slope = (math.log(a1) - math.log(a0)) / (c1 - c0)
    a5 = math.exp(math.log(a1) + slope * (c - c1))
    return max(a5 / _BASE_A5, _MIN_FACTOR), True, False


def apply_high_carbon_correction(mean, input_dict):
    """mean[2](연신율) 보정. (corrected_mean, info) 반환. mean은 변경하지 않고 복사한다."""
    import numpy as np

    corrected = np.array(mean, dtype=float)
    info = {"applied": False, "factor": 1.0, "c_pct": None,
            "extrapolated": False, "refused": False}
    if not isinstance(input_dict, dict) or "C" not in input_dict:
        return corrected, info
    try:
        c = float(input_dict["C"])
    except (TypeError, ValueError):
        return corrected, info
    if not math.isfinite(c):
        return corrected, info
    info["c_pct"] = c
    factor, extrapolated, refused = elongation_factor(c)
    info.update({"factor": factor, "extrapolated": extrapolated, "refused": refused})
    if refused or factor >= 1.0:
        return corrected, info
    corrected[2] = float(max(corrected[2] * factor, 0.0))
    info["applied"] = True
    return corrected, info


def correction_badge(info):
    """결과 화면용 한 줄 설명. 보정 없으면 빈 문자열."""
    if info.get("refused"):
        return ("보정 범위 초과 (C &gt; 2%) - 모델값을 그대로 표시합니다 "
                "(고C 외삽 보정 미적용)")
    if not info.get("applied"):
        return ""
    tag = "외삽" if info.get("extrapolated") else "실측구간"
    return (f"고C 외삽 보정 적용 ({tag}, C={info['c_pct']:.2f}%, "
            f"연신율 계수 {info['factor']:.2f}, SAE as-rolled 추세)")
