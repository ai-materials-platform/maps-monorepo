"""상·결정구조 + Schaeffler 판정 엔진 (simulation physics.js와 동일 로직).

ML 학습용 간이 당량( Ni+30C+0.5Mn+... )과 달리, 표시용으로는
Co/Ti/Al/Cu를 포함한 확장 Schaeffler-DeLong식을 사용한다.
Schaeffler는 용접/주조 스테인리스용 경험식이므로 단조+열처리재에는
참고용으로만 사용할 것.
"""

PHASE_CRYSTAL = {
    "austenite": {"symbol": "γ", "name": "오스테나이트", "structure": "FCC"},
    "ferrite": {"symbol": "α", "name": "페라이트", "structure": "BCC"},
    "martensite": {"symbol": "α'", "name": "마르텐사이트", "structure": "BCT"},
    "bainite": {"symbol": "B", "name": "베이나이트", "structure": "BCT"},
}


def compute_equivalents(comp):
    """확장 당량식. comp: 원소기호->wt% dict."""
    g = lambda k: float(comp.get(k, 0) or 0)
    ni_eq = g("Ni") + g("Co") + 30 * (g("C") + g("N")) + 0.5 * g("Mn") + 0.25 * g("Cu")
    cr_eq = g("Cr") + g("Mo") + 1.5 * g("Si") + 0.5 * g("Nb") + 2.0 * g("Ti") + 1.5 * g("Al")
    return ni_eq, cr_eq


def predict_phases(comp, method="empirical", T_K=1323.0):
    """상분율+판정. method='empirical'(기본, 빠름) 또는 'calphad'(정밀, 평형).

    calphad는 pycalphad+mc-fe DB가 필요하고, 불가하면 method='empirical-fallback'
    로 경험식을 반환한다.
    """
    if method == "calphad":
        try:
            from src.engine.calphad_engine import DISPLAY_MAP, calphad_available, calphad_phases
            if calphad_available():
                res = calphad_phases(comp, T_K=T_K)
                fracs = {"austenite": 0, "ferrite": 0, "martensite": 0, "bainite": 0}
                other = {}
                for ph, val in res["fractions"].items():
                    label = DISPLAY_MAP.get(ph)
                    if label in fracs:
                        fracs[label] += val * 100
                    elif ph != "LIQUID":
                        other[ph] = round(val * 100, 1)
                fracs = {k: int(round(val)) for k, val in fracs.items()}
                ni_eq, cr_eq = compute_equivalents(comp)
                zone = classify_schaeffler(ni_eq, cr_eq, fracs)
                return {
                    **fracs,
                    "Ni_eq": round(ni_eq, 1),
                    "Cr_eq": round(cr_eq, 1),
                    "schaeffler": zone,
                    "method": res["method"],
                    "T_K": res["T_K"],
                    "other_phases": other,
                    "ignored_elements": res["ignored_elements"],
                }
        except Exception:
            pass
        method = "empirical-fallback"
    ni_eq, cr_eq = compute_equivalents(comp)
    total_eq = ni_eq + cr_eq
    ratio = cr_eq / total_eq if total_eq > 0 else 0.5

    if ratio < 0.45:
        austenite = min(98, 70 + ni_eq * 0.60)
        ferrite = max(0, 100 - austenite - 2)
        martensite = 2
        bainite = 0
    elif ratio < 0.68:
        t = (ratio - 0.45) / 0.23
        ferrite = min(20, t * 20)
        austenite = max(75, 95 - ferrite)
        martensite = min(5, t * 5)
        bainite = 0
    else:
        t = min(1, (ratio - 0.68) / 0.20)
        ferrite = min(80, 45 + t * 35)
        martensite = min(40, t * 40)
        austenite = max(0, 100 - ferrite - martensite)
        bainite = 0

    s = austenite + ferrite + martensite + bainite
    k = 100 / s if s > 0 else 1
    fracs = {
        "austenite": round(austenite * k),
        "ferrite": round(ferrite * k),
        "martensite": round(martensite * k),
        "bainite": round(bainite * k),
    }
    zone = classify_schaeffler(ni_eq, cr_eq, fracs)
    return {
        **fracs,
        "Ni_eq": round(ni_eq, 1),
        "Cr_eq": round(cr_eq, 1),
        # WRC-1992 표준 축 (Kotecki & Siewert 1992). FN은 도표 판독값이라 위치값까지만 제공.
        "WRC_Ni_eq": round(float(comp.get("Ni", 0) or 0) + 35 * float(comp.get("C", 0) or 0) + 20 * float(comp.get("N", 0) or 0) + 0.25 * float(comp.get("Cu", 0) or 0), 2),
        "WRC_Cr_eq": round(float(comp.get("Cr", 0) or 0) + float(comp.get("Mo", 0) or 0) + 0.7 * float(comp.get("Nb", 0) or 0), 2),
        "schaeffler": zone,
        "method": method if method != "empirical" else "empirical (Schaeffler)",
    }


def predict_from_equivalents(ni_eq, cr_eq):
    """Ni_eq/Cr_eq 직접 입력으로부터 상분율+판정 (공정조건 패널용)."""
    ni_eq = float(ni_eq or 0)
    cr_eq = float(cr_eq or 0)
    total_eq = ni_eq + cr_eq
    ratio = cr_eq / total_eq if total_eq > 0 else 0.5

    if ratio < 0.45:
        austenite = min(98, 70 + ni_eq * 0.60)
        ferrite = max(0, 100 - austenite - 2)
        martensite = 2
        bainite = 0
    elif ratio < 0.68:
        t = (ratio - 0.45) / 0.23
        ferrite = min(20, t * 20)
        austenite = max(75, 95 - ferrite)
        martensite = min(5, t * 5)
        bainite = 0
    else:
        t = min(1, (ratio - 0.68) / 0.20)
        ferrite = min(80, 45 + t * 35)
        martensite = min(40, t * 40)
        austenite = max(0, 100 - ferrite - martensite)
        bainite = 0

    s = austenite + ferrite + martensite + bainite
    k = 100 / s if s > 0 else 1
    fracs = {
        "austenite": round(austenite * k),
        "ferrite": round(ferrite * k),
        "martensite": round(martensite * k),
        "bainite": round(bainite * k),
    }
    return {
        **fracs,
        "Ni_eq": round(ni_eq, 1),
        "Cr_eq": round(cr_eq, 1),
        "schaeffler": classify_schaeffler(ni_eq, cr_eq, fracs),
    }


def classify_schaeffler(ni_eq, cr_eq, phases):
    a = phases.get("austenite", 0)
    f = phases.get("ferrite", 0)
    m = phases.get("martensite", 0)

    order = sorted(
        [("austenite", a), ("ferrite", f), ("martensite", m)],
        key=lambda x: x[1], reverse=True,
    )
    dominant = order[0][0]

    if a >= 90:
        zone, zone_ko = "A", "완전 오스테나이트"
        desc = "γ-FCC 단상 영역. 연성·인성이 높고 가공경화 경향"
    elif a >= 60:
        zone, zone_ko = "A+F", "오스테나이트 + 페라이트"
        desc = "γ-FCC 기지에 α-BCC 소량. 강도↑·내응력부식 균형 영역"
    elif f >= 45 and m >= 15:
        zone, zone_ko = "F+M", "페라이트 + 마르텐사이트"
        desc = "α-BCC + α'-BCT. 고강도·저연성, 취화 주의 영역"
    elif f >= 45:
        zone, zone_ko = "F+A", "페라이트 + 오스테나이트"
        desc = "α-BCC 주상. 강도↑·연신율↓, 듀플렉스 경계 영역"
    elif m >= 20:
        zone, zone_ko = "M", "마르텐사이트 우세"
        desc = "α'-BCT 우세. 최고 강도·최저 연성, 퀜칭 조직"
    else:
        zone, zone_ko = "MIX", "혼합 조직"
        desc = "오스테나이트·페라이트·마르텐사이트 혼합 영역"

    return {
        "zone": zone,
        "zoneKo": zone_ko,
        "description": desc,
        "dominantPhase": dominant,
        "dominantCrystal": PHASE_CRYSTAL[dominant]["structure"],
        "lowAlloy": bool(ni_eq < 2 and cr_eq < 5),
    }
