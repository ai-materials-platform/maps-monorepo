# CALPHAD 데이터 (`data/calphad/`)

## mc_fe.tdb (368 KB)

- 원본: MatCalc 오픈 철강 DB `mc_fe` v2.057 (TU Wien, Povoden-Karadeniz)
  - 출처: https://github.com/wuhao-tit/Thermodynamic-database (`mc_fe_v2.057.tdb`)
- 정제: `scripts/calphad_cleantdb.py` (MatCalc 방언 → Thermo-Calc/pycalphad 파싱용)
  - 제거: `REFERENCE_ELEMENT`, `ADD_COMPOSITION_SET`, `ATTACH_CONTRIBUTION`,
    `HMVA` 몰부피 파라미터, `BCC_DISL` 테스트상, 꼬리 문서, 공백 포함 REF 정규화,
    `.00` 온도 표기, `> >> n` 힌트, 빈 2구간
  - **주의**: G(깁스에너지) 파라미터는 손대지 않았으나, B2 규칙화 연결 해제로
    Al-rich B2 영역은 신뢰도 낮음. BCC_DISL(전위) 상 제거.
- 검증(1323 K): 순수 Fe 1200K→FCC / 1000K→BCC, 304→FCC, 316→FCC. 전부 정답.
- 용도: 평형 상분율 정밀 계산용. 경험식 표시의 폴백이 아니라 상위 수단.
- 원본 파일은 외부 URL에서 받음. 라이선스: MatCalc 무료 DB (연구·교육용).
