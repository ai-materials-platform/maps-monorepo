"""CALPHAD 평형 상분율 엔진 (mc-fe DB + pycalphad).

경험식(phase_engine.predict_phases)의 상위 수단. 조성(wt%)+온도(K)를 받아
평형 상분율을 계산한다. 평형 가정이므로 급랭·용접 조직(비평형)과는 차이 가능.

사용법:
    from src.engine.calphad_engine import calphad_available, calphad_phases
    calphad_phases({"Fe": 68, "Cr": 17, "Ni": 12, "Mo": 2}, T_K=1323.0)
"""
from pathlib import Path

AT_MASS = {
    "FE": 55.845, "CR": 51.9961, "NI": 58.6934, "MO": 95.95,
    "MN": 54.938, "SI": 28.0855, "C": 12.011, "N": 14.007,
    "NB": 92.906, "TI": 47.867, "AL": 26.9815, "CO": 58.933,
    "CU": 63.546, "V": 50.9415, "W": 183.84,
}

TDB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "calphad" / "mc_fe.tdb"

PHASES = ["FCC_A1", "BCC_A2", "LIQUID", "CEMENTITE", "M23C6", "M7C3",
          "SIGMA", "LAVES_PHASE", "CHI_A12", "G_PHASE"]

# 표시 매핑: CALPHAD 상 → 우리 상 라벨
DISPLAY_MAP = {
    "FCC_A1": "austenite",
    "BCC_A2": "ferrite",
    "LIQUID": None,  # 용융상은 분율 표시에서 제외하고 별도 표기
}

_db = None


def calphad_available():
    if not TDB_PATH.exists():
        return False
    try:
        import pycalphad  # noqa: F401
        return True
    except ImportError:
        return False


def _get_db():
    global _db
    if _db is None:
        from pycalphad import Database
        _db = Database(str(TDB_PATH))
    return _db


def _wt_to_mole(wt):
    moles = {}
    for sym, val in wt.items():
        key = sym.upper()
        if key in AT_MASS and val:
            moles[key] = float(val) / AT_MASS[key]
    total = sum(moles.values())
    if total <= 0:
        raise ValueError("유효한 조성이 없습니다.")
    return {k: v / total for k, v in moles.items()}


def calphad_phases(composition_wt, T_K=1323.0):
    """평형 상분율 계산. 반환: {phase_name: mole_fraction} + 'T_K'.

    composition_wt: {'Fe': 68, 'Cr': 17, ...} (wt%, 대소문자 무관).
    DB에 없는 원소는 무시된다는 점에 주의(반환에 'ignored' 기록).
    """
    from pycalphad import equilibrium, variables as v

    db = _get_db()
    x = _wt_to_mole(composition_wt or {})
    ignored = [s for s in (composition_wt or {}) if s.upper() not in AT_MASS]
    comps = list(x) + ["VA"]
    conds = {v.T: float(T_K), v.P: 101325}
    for c in list(x)[1:]:
        conds[v.X(c)] = x[c]
    phases = [p for p in PHASES if p in db.phases]
    eq = equilibrium(db, comps, phases, conds, verbose=False)

    fracs = {}
    for ph, npf in zip(eq.Phase.values.flat, eq.NP.values.flat):
        name = str(ph)
        val = float(npf)
        if name and val == val and val > 1e-6:
            fracs[name] = fracs.get(name, 0.0) + val
    total = sum(fracs.values()) or 1.0
    fracs = {k: val / total for k, val in fracs.items()}
    return {"fractions": fracs, "T_K": float(T_K), "ignored_elements": ignored,
            "method": "CALPHAD-equilibrium (mc-fe)"}
