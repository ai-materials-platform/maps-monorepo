"""독립 검증: hea_database 등원자(equiatomic) FeCrNi 실험행으로 구/신 Al 계수 비교.

등원자 행(숫자 없음, 예 AlCoCrFeNi)은 단위 혼재 문제에서 자유로워 독립 검증용으로 적합.
당량식은 여기서 직접 계산하고, 판정은 phase_engine.predict_from_equivalents 재사용.
"""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.engine.phase_engine import predict_from_equivalents

TMP = Path(r"C:\Users\jjs45\AppData\Local\Temp\opencode") / "database_of_HEAs.csv"
TOKEN = re.compile(r"([A-Z][a-z]?)(\d+(?:\.\d+)?)?")


def parse(name):
    toks = TOKEN.findall((name or "").strip())
    if not toks or "".join(s + (n or "") for s, n in toks) != (name or "").strip():
        return None
    return [(s, float(n) if n else 1.0) for s, n in toks]


def equiv(comp, al_coef):
    g = lambda k: comp.get(k, 0.0)
    ni = g("Ni") + g("Co") + 30 * (g("C") + g("N")) + 0.5 * g("Mn") + 0.25 * g("Cu")
    cr = g("Cr") + g("Mo") + 1.5 * g("Si") + 0.5 * g("Nb") + 2.0 * g("Ti") + al_coef * g("Al")
    return ni, cr


FAM = {"austenite": "FCC", "ferrite": "BCC", "martensite": "BCT", "bainite": "BCT"}

rows = list(csv.DictReader(open(TMP, encoding="utf-8")))
pool = []
for r in rows:
    if (r.get("Experimental or theoretical") or "").strip().lower() != "experimental":
        continue
    toks = parse((r.get("Alloy") or "").strip())
    if toks is None or any(v != 1.0 for _, v in toks):
        continue  # 등원자만
    syms = {s for s, _ in toks}
    if not {"Fe", "Cr", "Ni"} <= syms:
        continue
    obs = (r.get("Phase") or "").strip()
    fams = set()
    if "FCC" in obs:
        fams.add("FCC")
    if "BCC" in obs:
        fams.add("BCC")
    if not fams:
        continue
    n = len(toks)
    comp = {s: 100.0 / n for s, _ in toks}
    pool.append((obs, fams, comp))

print(f"equiatomic FeCrNi experimental rows: {len(pool)}")
for al in (1.5, 2.5):
    hit = tot = 0
    for obs, fams, comp in pool:
        ni, cr = equiv(comp, al)
        dom = predict_from_equivalents(ni, cr)["schaeffler"]["dominantPhase"]
        tot += 1
        if FAM[dom] in fams:
            hit += 1
    print(f"Al coef {al}: {hit}/{tot} = {hit / max(tot, 1) * 100:.1f}%")
