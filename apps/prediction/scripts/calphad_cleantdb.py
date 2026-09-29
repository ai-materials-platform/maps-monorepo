"""MatCalc TDB → pycalphad 파싱 정리. 사용법: python calphad_cleantdb.py [SRC] [DST]."""
import io
import re
import sys

from pycalphad import Database

SRC = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\jjs45\AppData\Local\Temp\opencode\mc_x.tdb"
DST = sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\jjs45\AppData\Local\Temp\opencode\mc_x_clean.tdb"
raw = open(SRC, encoding="latin-1").read().splitlines()
lines = ["".join(c if ord(c) < 128 else "?" for c in ln) for ln in raw]
# MatCalc trailing '.00' quirk: '6000.00.00' -> '6000.00', '44.0.00' -> '44.0'
lines = [re.sub(r"(\d+\.\d+)\.00\b", r"\1", ln) for ln in lines]
# 빈 2구간 '; 6000 N ; 6000.00 N' → '; 6000.00 N' (표현식 없는 축퇴 구간)
lines = [ln.replace("; 6000 N ; 6000.00  N", "; 6000.00  N") for ln in lines]
# MatCalc 주성분 힌트 '> >> n' (CONSTITUENT 뒤 꼬리표, G 무관) 제거
lines = [re.sub(r">\s*>>\s*\d+", "", ln) for ln in lines]
# 파일 끝 MatCalc 평가문서(명령 아님, '$' 주석 표시 없음) 절단
for i, ln in enumerate(lines):
    if re.match(r"(?i)^[A-Z]\d+-\d+\s+(unary|binary|ternary|higher)\b", ln):
        print(f"truncate trailing docs at L{i + 1}: {ln[:60]}")
        lines = lines[:i]
        break
# REF 텍스트는 G와 무관 + 공백 포함 시 파서 오류 유발 → 'REF:0'으로 정규화
lines = [re.sub(r"REF\s*:[^!]*(!)", r"REF:0 \1", ln) for ln in lines]
# BCC_DISL: 전위 Cottrell 분위기 테스트상(주석 명시). 벌크 평형과 무관 → 블록 통째 제거
start = next((i for i, ln in enumerate(lines) if re.match(r"\s*PHASE\s+BCC_DISL\b", ln)), None)
if start is not None:
    end = start
    while end + 1 < len(lines) and not re.match(r"\s*TYPE_DEFINITION", lines[end + 1]):
        end += 1
    print(f"pre-remove BCC_DISL block L{start + 1}-L{end + 1}")
    del lines[start:end + 1]

SAFE_SINGLE = re.compile(r"\s*(REFERENCE_ELEMENT|REJECT_PHASE|RESTORE_PHASE|SET_ALL_START|HALT|SET_EVALUATION_STRING|ADD_COMPOSITION_SET|ATTACH_CONTRIBUTION)\b")

for round in range(300):
    try:
        db = Database(io.StringIO("\n".join(lines)))
        print("PARSE OK, phases:", len(db.phases))
        open(DST, "w", encoding="ascii").write("\n".join(lines))
        break
    except Exception as e:
        m = re.search(r"\(line:(\d+),", str(e))
        print(f"[round {round}]", str(e)[:200].replace("\n", " | "))
        if not m:
            break
        idx = int(m.group(1)) - 1
        if SAFE_SINGLE.match(lines[idx]):
            print("  -> removing:", lines[idx][:70])
            del lines[idx]
        elif re.match(r"\s*PARAMETER\s+HMVA\(", lines[idx]):
            end = idx
            while end < len(lines) and "!" not in lines[end]:
                end += 1
            print(f"  -> removing HMVA block L{idx + 1}-L{end + 1} (molar volume, G무관)")
            del lines[idx:end + 1]
        else:
            print("  -> NOT safe, context:")
            for j in range(max(0, idx - 2), min(len(lines), idx + 3)):
                print(f"    L{j + 1}: {lines[j][:100]}")
            break
