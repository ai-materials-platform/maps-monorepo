# 다크모드 2차 — 시뮬 내부 색 목록

1차(2026-10-25, UI 통일 Task 5)는 화면 틀만 `--maps-*`에 연결했다. 아래는 다크에서도 밝게 남는 고정 색이다(목록만, 고치지 않음).
`grep`으로 뽑은 배경 기준: `#F…`·`#fff`·`white`·`rgba(255,…)`.

## 3D 뷰 위 겹침 라벨·컬러맵 (`apps/simulation/src/styles.css`)
- 381 `.holo-label`, 425 `.cae-colormap`, 465 `.cae-unit-label`

## 3D 뷰·대화상자 인라인 색 (`apps/simulation/src/App.jsx`)
- 1143, 1167 — 합금 이름 대화상자(흰 카드·회색 버튼)
- 1383 — URL 입력칸
- 1527 — 뷰 오른쪽 아래 응력 범례
- 3581, 3839 — 3D 뷰 겹침 패널(반투명 흰색, `#d0cdc6` 테두리)

## 보고서 모달 (인쇄용 흰 종이 — 다크에서도 흰색 유지가 맞는지 먼저 결정)
- `src/styles.css` 654 `.report-backdrop`, 665 `.report-modal`
- `src/components/ReportModal.jsx` 156, 168, 231, 506, 546, 566, 624, 659, 671, 682, 696, 699, 719
- `src/components/ReportModalDigitalTwin.jsx` 42, 67, 119, 174, 186, 187
- `src/components/ReportModalKoreanSimple.jsx` 40, 65, 118, 175, 187, 188

## 그 밖
- 3D 장면 배경·바닥(`#0B1020` 계열), 컬러맵 그라데이션, 차트 선 색은 원래 색 유지가 기본.
