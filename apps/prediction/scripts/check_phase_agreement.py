"""1번 검증: 우리 경험식 주상 예측 vs 실측 라벨(IDEAsLab 323) 일치율.

방법(한계 명시):
 - IDEAsLab alloy_name(원자비)을 wt% 자리에 그대로 투입. 당량식은 원래 wt% 기준이라
   근사이며, 앱(frontend predictPhases)도 동일 방식으로 계산하므로 앱 동작 그대로의 검증임.
 - 식에 없는 원소(Ta/Zr/Hf 등)는 0으로 무시.
 - 관측 라벨의 FCC/BCC 패밀리와 예측 주상(austenite=FCC, ferrite=BCC) 포함 관계로 판정.
   IM 포함 행은 우리 식이 IM을 모르므로 별도 집계.
"""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.engine.phase_engine import predict_phases

TMP = Path(r"C:\Users\jjs45\AppData\Local\Temp\opencode") / "db_HEAs.csv"
TOKEN = re.compile(r"([A-Z][a-z]?)(\d+(?:\.\d+)?)?")


def parse(name):
    toks = TOKEN.findall((name or "").strip())
    if not toks or "".join(s + (n or "") for s, n in toks) != name.strip():
        return None
    return {s: (float(n) if n else 1.0) for s, n in toks}


FAM = {"austenite": "FCC", "ferrite": "BCC", "martensite": "BCT", "bainite": "BCT"}

rows = list(csv.DictReader(open(TMP, encoding="utf-8")))
total = hit = im_only = im_mixed = 0
miss_detail = {}
for r in rows:
    comp = parse(r["alloy_name"])
    if comp is None:
        continue
    tot = sum(comp.values())
    wt = {k: v / tot * 100 for k, v in comp.items()}
    pred = predict_phases(wt)
    dom = pred["schaeffler"]["dominantPhase"]
    pf = FAM[dom]
    obs = r["phases"]
    obs_fams = set()
    if "FCC" in obs:
        obs_fams.add("FCC")
    if "BCC" in obs:
        obs_fams.add("BCC")
    has_im = "Im" in obs
    total += 1
    if not obs_fams:  # IM 단독: 우리 식으로 맞힐 수 없음
        im_only += 1
        continue
    if has_im:
        im_mixed += 1
    if pf in obs_fams:
        hit += 1
    else:
        miss_detail[obs] = miss_detail.get(obs, 0) + 1

print(f"total={total} hit={hit} ({hit / max(total - im_only, 1) * 100:.1f}% of FCC/BCC-containing)")
print(f"IM-only rows (unpredictable by design)={im_only}, IM-mixed rows={im_mixed}")
print("miss by observed label:", miss_detail)
