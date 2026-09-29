"""CALPHAD 평형 계산 스모크 테스트 (316 조성, 1323 K)."""
import os
import sys

import pycalphad
from pycalphad import Database, equilibrium, variables as v

TDB = os.path.dirname(pycalphad.__file__) + "/tests/databases/mc_fecocrnbti.tdb"

AT_MASS = {"FE": 55.845, "CR": 51.9961, "NI": 58.6934, "MO": 95.95,
           "MN": 54.938, "SI": 28.0855, "C": 12.011, "N": 14.007}


def wt_to_mole(wt):
    moles = {k: wt[k] / AT_MASS[k] for k in wt}
    tot = sum(moles.values())
    return {k: moles[k] / tot for k in moles}


def calc(wt, T=1323.0):
    db = Database(TDB)
    comps = ["FE", "CR", "NI", "MO", "MN", "SI", "C", "N", "VA"]
    phases = ["FCC_A1", "BCC_A2", "LIQUID", "M23C6", "M7C3", "SIGMA", "LAVES_PHASE", "CHI_A12"]
    x = wt_to_mole({k: wt.get(k, 0.0) for k in comps if k != "VA"})
    conds = {v.T: T, v.P: 101325}
    for c in comps[1:]:
        if c == "VA":
            continue
        conds[v.X(c)] = x[c]
    eq = equilibrium(db, comps, phases, conds, verbose=False)
    npf = eq.NP.values
    out = {}
    for i, ph in enumerate(eq.Phase.values.flat):
        name = str(ph)
        out[name] = out.get(name, 0.0) + float(npf.flat[i])
    return {k: round(val, 4) for k, val in sorted(out.items()) if val > 1e-4}


if __name__ == "__main__":
    # 316 (wt%): Fe bal, Cr 17, Ni 12, Mo 2, Mn 1.2, Si 0.5, C 0.03, N 0.04
    wt = {"FE": 67.21, "CR": 17.0, "NI": 12.0, "MO": 2.0,
          "MN": 1.2, "SI": 0.5, "C": 0.03, "N": 0.04}
    print(calc(wt))
