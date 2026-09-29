"""외부 실측 상(phase) 데이터 수집 → phase_data.xml 생성.

입력(오픈 데이터, 수집일 2026-09-29):
  1. IDEAsLab-Materials-Informatics/ML-phase-fraction-MPEAs, db_HEAs.csv (MIT)
     - 323개 다중주원소합금, 실험 관측 상 라벨(FCC/BCC/IM 조합) + 정규모델 피처
     - 원논문: Beniwal & Ray, Comput. Mater. Sci. 2021, doi:10.1016/j.commatsci.2021.110647
  2. Vladimirchizh/hea_database, database_of_HEAs.csv (CC-BY-4.0)
     - 논문에서 LLM 추출한 HEA 상 데이터 12427행 중 Fe+Cr+Ni 포함 실험행만 발췌
     - 합금 표기는 원문 그대로(verbatim) 보존. 숫자 혼합(at%·몰비 혼재)이라 정규화하지 않음.

출력: apps/prediction/data/raw/phase_data.xml
"""
import csv
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

IDEAS_URL = "https://raw.githubusercontent.com/IDEAsLab-Materials-Informatics/ML-phase-fraction-MPEAs/main/db_HEAs.csv"
HEA_URL = "https://raw.githubusercontent.com/Vladimirchizh/hea_database/main/database_of_HEAs.csv"

HERE = Path(__file__).resolve()
OUT = HERE.parent.parent / "data" / "raw" / "phase_data.xml"
TMP = Path(r"C:\Users\jjs45\AppData\Local\Temp\opencode")

TOKEN = re.compile(r"([A-Z][a-z]?)(\d+(?:\.\d+)?)?")


def parse_alloy(name):
    """'Al0.25MoNbTiV' → [(Al,0.25),(Mo,1),...]. 숫자 없으면 1. 실패 시 None."""
    if not name or not isinstance(name, str):
        return None
    toks = TOKEN.findall(name.strip())
    if not toks:
        return None
    joined = "".join(s + (n or "") for s, n in toks)
    if joined != name.strip():
        return None
    return [(s, float(n) if n else 1.0) for s, n in toks]


def main():
    ideas_path = TMP / "db_HEAs.csv"
    hea_path = TMP / "database_of_HEAs.csv"
    if not ideas_path.exists():
        urllib.request.urlretrieve(IDEAS_URL, ideas_path)
    if not hea_path.exists():
        urllib.request.urlretrieve(HEA_URL, hea_path)

    root = ET.Element("phase_data", collected="2026-09-29")

    meta = ET.SubElement(root, "metadata")
    ET.SubElement(meta, "note").text = (
        "실험 관측 상 라벨 데이터. 정량 상분율(vol%)이 아니라 관측된 상 조합 라벨임에 주의. "
        "스테인리스 용접부 페라이트수(FN) 실측 테이블 형태의 오픈 데이터는 찾지 못함. "
        "Schaeffler/WRC-1992 도표법은 방법론 참고문헌으로만 인용."
    )
    for title, url, lic in [
        ("IDEAsLab ML-phase-fraction-MPEAs db_HEAs.csv",
         "https://github.com/IDEAsLab-Materials-Informatics/ML-phase-fraction-MPEAs", "MIT"),
        ("Vladimirchizh hea_database database_of_HEAs.csv",
         "https://github.com/Vladimirchizh/hea_database", "CC-BY-4.0 (attribution required)"),
    ]:
        s = ET.SubElement(meta, "source", license=lic)
        ET.SubElement(s, "title").text = title
        ET.SubElement(s, "url").text = url
    for title, url in [
        ("Beniwal & Ray (2021), Comp. Mater. Sci., doi:10.1016/j.commatsci.2021.110647",
         "https://doi.org/10.1016/j.commatsci.2021.110647"),
        ("Kotecki & Siewert (1992), WRC-1992 constitution diagram, Welding Journal 71:171s-178s",
         "https://s3.us-east-1.amazonaws.com/WJ-www.aws.org/supplement/WJ_1992_05_s171.pdf"),
        ("NRC Welding Metallurgy training (Schaeffler/DeLong/WRC-1992 equivalents table)",
         "https://www.nrc.gov/docs/ML1215/ML12157A615.pdf"),
        ("NIST SP 260-141 secondary ferrite number reference materials",
         "https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication260-141.pdf"),
    ]:
        r = ET.SubElement(meta, "reference")
        ET.SubElement(r, "title").text = title
        ET.SubElement(r, "url").text = url

    # --- dataset 1: IDEAsLab 323 ---
    ds1 = ET.SubElement(root, "dataset", name="ideaslab-mpea-323",
                        license="MIT",
                        paper_doi="10.1016/j.commatsci.2021.110647")
    ET.SubElement(ds1, "description").text = (
        "323 multi-principal element alloys with experimentally observed phase labels. "
        "alloy_name parsed to atomic ratios (missing subscript = 1)."
    )
    n1 = n1_skip = 0
    with open(ideas_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            toks = parse_alloy(row["alloy_name"])
            if toks is None:
                n1_skip += 1
                continue
            total = sum(v for _, v in toks)
            rec = ET.SubElement(ds1, "record", id=str(n1))
            ET.SubElement(rec, "alloy").text = row["alloy_name"]
            comp = ET.SubElement(rec, "composition", unit="atomic_ratio")
            for sym, val in toks:
                ET.SubElement(comp, "element", symbol=sym,
                              atomic_fraction=f"{val / total:.4f}").text = str(val)
            ET.SubElement(rec, "observed_phases").text = row["phases"]
            ET.SubElement(rec, "phase_code").text = row["phase_code"]
            n1 += 1
    ds1.set("records", str(n1))
    ds1.set("skipped_unparseable", str(n1_skip))

    # --- dataset 2: hea_database Fe-Cr-Ni experimental subset ---
    ds2 = ET.SubElement(root, "dataset", name="hea-database-fecrni-experimental",
                        license="CC-BY-4.0",
                        note="LLM-extracted from papers; quality varies. alloy kept verbatim, no normalization.")
    ET.SubElement(ds2, "description").text = (
        "Rows containing Fe+Cr+Ni, experimental only, informative phase labels. "
        "Composition numbers mix at% and molar ratios across rows — do not compare magnitudes directly."
    )
    DROP_PHASES = {"not specified", "cubic", "not explicitly mentioned", ""}
    n2 = n2_skip = 0
    with open(hea_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row.get("Experimental or theoretical") or "").strip().lower() != "experimental":
                continue
            alloy = (row.get("Alloy") or "").strip()
            toks = parse_alloy(alloy)
            if toks is None or not {"Fe", "Cr", "Ni"} <= {s for s, _ in toks}:
                n2_skip += 1
                continue
            phase = (row.get("Phase") or "").strip()
            if phase.lower() in DROP_PHASES:
                n2_skip += 1
                continue
            rec = ET.SubElement(ds2, "record", id=str(n2))
            ET.SubElement(rec, "alloy_verbatim").text = alloy
            comp = ET.SubElement(rec, "composition_tokens", unit="as_reported")
            for sym, val in toks:
                ET.SubElement(comp, "element", symbol=sym).text = str(val)
            ET.SubElement(rec, "observed_phases").text = phase
            ET.SubElement(rec, "n_phases").text = (row.get("Nb of phase") or "").strip()
            ET.SubElement(rec, "paper").text = (row.get("Paper") or "").strip()
            ET.SubElement(rec, "experimental_details").text = (row.get("Experimental details") or "").strip()
            ET.SubElement(rec, "special_conditions").text = (row.get("Special conditions") or "").strip()
            n2 += 1
    ds2.set("records", str(n2))
    ds2.set("skipped", str(n2_skip))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    xml_str = minidom.parseString(ET.tostring(root, encoding="unicode")).toprettyxml(indent="  ")
    OUT.write_text(xml_str, encoding="utf-8")
    print(f"wrote {OUT}  (ds1={n1} skip={n1_skip}, ds2={n2} skip={n2_skip})")


if __name__ == "__main__":
    main()
