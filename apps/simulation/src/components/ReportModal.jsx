import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { predictPhases, classifyFracture, estimateHardness, estimateKIC, generateSNCurve } from "../lib/physics.js";
import { latticeEstimates } from "./LatticeViewer.jsx";

// ── Mini stress-strain SVG for the report ──────────────────────────────────
function ReportSSChart({ points, UTS, YS, elongPct }) {
  if (!points || points.length < 2) return null;
  const W = 320, H = 160;
  const padL = 42, padB = 28, padR = 10, padT = 14;
  const w = W - padL - padR, h = H - padB - padT;

  const maxStrain = elongPct || 20;
  const pts = points.map((p, i) => {
    const x = padL + (p.strainPct / maxStrain) * w;
    const y = padT + h - (p.stressMpa / UTS) * h;
    return `${x},${y}`;
  }).join(" ");

  const yieldX = padL + ((YS / UTS) * (YS / (points[points.length-1]?.stressMpa || UTS)) * w);

  return (
    <svg width={W} height={H} style={{ fontFamily: "monospace", fontSize: 9 }}>
      {/* Grid */}
      {[0, 0.25, 0.5, 0.75, 1].map(v => (
        <g key={v}>
          <line x1={padL} y1={padT + h * (1-v)} x2={W - padR} y2={padT + h * (1-v)}
            stroke="#e0ddd8" strokeWidth="0.5" />
          <text x={padL - 4} y={padT + h * (1-v) + 3} textAnchor="end" fill="#888" fontSize={8}>
            {Math.round(UTS * v)}
          </text>
        </g>
      ))}
      {/* Strain axis labels */}
      {[0, 0.5, 1].map(v => (
        <text key={v} x={padL + w * v} y={H - 6} textAnchor="middle" fill="#888" fontSize={8}>
          {(maxStrain * v).toFixed(0)}%
        </text>
      ))}
      {/* Axis labels */}
      <text x={10} y={H / 2} textAnchor="middle" fill="#555" fontSize={9}
        transform={`rotate(-90, 10, ${H / 2})`}>응력 (MPa)</text>
      <text x={W / 2} y={H - 1} textAnchor="middle" fill="#555" fontSize={9}>변형률 (%)</text>
      {/* Yield line */}
      <line x1={yieldX} y1={padT} x2={yieldX} y2={padT + h}
        stroke="#b45309" strokeWidth={1} strokeDasharray="4,3" opacity={0.7} />
      <text x={yieldX + 2} y={padT + 10} fill="#b45309" fontSize={8}>항복점</text>
      {/* UTS line */}
      <line x1={padL + w * 0.785} y1={padT} x2={padL + w * 0.785} y2={padT + h}
        stroke="#c0392b" strokeWidth={1} strokeDasharray="4,3" opacity={0.7} />
      <text x={padL + w * 0.787} y={padT + 10} fill="#c0392b" fontSize={8}>UTS</text>
      {/* Curve fill */}
      <polygon
        points={`${padL},${padT + h} ${pts} ${padL + (elongPct / maxStrain) * w},${padT + h}`}
        fill="#1a5fa8" opacity={0.08}
      />
      {/* Curve line */}
      <polyline points={pts} fill="none" stroke="#1a5fa8" strokeWidth={2}
        strokeLinecap="round" strokeLinejoin="round" />
      {/* Axes */}
      <line x1={padL} y1={padT} x2={padL} y2={padT + h} stroke="#ccc" strokeWidth={1} />
      <line x1={padL} y1={padT + h} x2={W - padR} y2={padT + h} stroke="#ccc" strokeWidth={1} />
    </svg>
  );
}

// ── Fatigue S-N Chart ────────────────────────────────────────────────────────
function ReportSNChart({ snCurve, Se }) {
  if (!snCurve || snCurve.length < 2) return null;
  const W = 280, H = 130;
  const padL = 40, padB = 24, padR = 10, padT = 10;
  const w = W - padL - padR, h = H - padB - padT;
  const maxS = Math.max(...snCurve.map(p => p.S)) * 1.05;
  const pts = snCurve.map(p => {
    const x = padL + ((p.logN - 1) / 7) * w;
    const y = padT + h - (p.S / maxS) * h;
    return `${x},${y}`;
  }).join(" ");
  const seY = padT + h - (Se / maxS) * h;
  return (
    <svg width={W} height={H} style={{ fontFamily: "monospace", fontSize: 8 }}>
      <line x1={padL} y1={seY} x2={W - padR} y2={seY}
        stroke="#217a3c" strokeWidth={1} strokeDasharray="3,2" opacity={0.8} />
      <text x={padL + 2} y={seY - 2} fill="#217a3c" fontSize={7.5}>내구한도 {Se?.toFixed(0)} MPa</text>
      <polyline points={pts} fill="none" stroke="#c0392b" strokeWidth={2}
        strokeLinecap="round" strokeLinejoin="round" />
      {[1,3,5,7].map(v => (
        <g key={v}>
          <line x1={padL + (v/7)*w} y1={padT} x2={padL + (v/7)*w} y2={padT+h}
            stroke="#eee" strokeWidth={0.5} />
          <text x={padL + (v/7)*w} y={H-6} textAnchor="middle" fill="#888" fontSize={7}>
            10{String(v+1).split("").map(d => "⁰¹²³⁴⁵⁶⁷⁸⁹"[d]).join("")}
          </text>
        </g>
      ))}
      {[0, 0.5, 1].map(v => (
        <text key={v} x={padL-2} y={padT + h*(1-v)+3} textAnchor="end" fill="#888" fontSize={7}>
          {Math.round(maxS * v)}
        </text>
      ))}
      <line x1={padL} y1={padT} x2={padL} y2={padT+h} stroke="#ccc" strokeWidth={1} />
      <line x1={padL} y1={padT+h} x2={W-padR} y2={padT+h} stroke="#ccc" strokeWidth={1} />
      <text x={W/2} y={H-1} textAnchor="middle" fill="#555" fontSize={8}>반복 횟수 (cycles)</text>
    </svg>
  );
}

// ── Microstructure Phase Bar ─────────────────────────────────────────────────
function PhaseBar({ phases }) {
  const colors = { austenite: "#1a5fa8", ferrite: "#217a3c", martensite: "#c0392b", bainite: "#b45309" };
  const labels = {
    austenite: "오스테나이트 γ-FCC",
    ferrite: "페라이트 α-BCC",
    martensite: "마르텐사이트 α'-BCT",
    bainite: "베이나이트 BCT",
  };
  const sch = phases?.schaeffler;
  return (
    <div>
      <div style={{ display: "flex", height: 14, borderRadius: 3, overflow: "hidden", marginBottom: 4 }}>
        {Object.entries(phases).filter(([k]) => colors[k] && phases[k] > 0).map(([k, v]) => (
          <div key={k} style={{ width: `${v}%`, background: colors[k] }} title={`${labels[k]}: ${v}%`} />
        ))}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 12px" }}>
        {Object.entries(phases).filter(([k]) => colors[k]).map(([k, v]) => (
          <span key={k} style={{ fontSize: 10, color: "#444", display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: colors[k], display: "inline-block" }} />
            {labels[k]}: <strong>{v}%</strong>
          </span>
        ))}
      </div>
      {sch && (
        <div style={{ marginTop: 6, padding: "6px 8px", background: "#EEF6FF", border: "1px solid #BFDBFE", borderRadius: 4, fontSize: 10, color: "#334155", lineHeight: 1.5 }}>
          <strong>Schaeffler 판정: {sch.zone} · {sch.zoneKo}</strong>
          <div>{sch.description}</div>
          <div>주상: {sch.dominantPhase} ({sch.dominantCrystal}) · Ni_eq {phases.Ni_eq} / Cr_eq {phases.Cr_eq}</div>
          <div>WRC-1992 위치: Cr_eq {phases.WRC_Cr_eq} / Ni_eq {phases.WRC_Ni_eq} (FN은 도표 판독, 본 보고서는 미기재)</div>
          {sch.lowAlloy && <div style={{ color: "#b45309" }}>저합금 조성이라 판정은 참고용입니다.</div>}
        </div>
      )}
    </div>
  );
}

// ── Minimal markdown renderer (headings / tables / lists / bold / hr / slots) ──
function renderInline(text, keyBase) {
  const parts = String(text).split(/(\*\*[^*]+\*\*|@\d+\([^)]*\)|`[^`]+`|\[[^\]]+\]\([^)]*\))/g);
  return parts.map((p, i) => {
    const kb = `${keyBase}-${i}`;
    let m = /^\*\*(.+)\*\*$/.exec(p);
    if (m) return <strong key={kb}>{m[1]}</strong>;
    m = /^@(\d+)\(([^)]*)\)$/.exec(p);
    if (m) return <span key={kb} style={{ fontSize: Number(m[1]) }}>{renderInline(m[2], kb)}</span>;
    m = /^`([^`]+)`$/.exec(p);
    if (m) return <code key={kb} style={{ background: "#f1f5f9", border: "1px solid #e2e8f0", borderRadius: 3, padding: "0 4px", fontSize: 10, fontFamily: "Consolas,monospace" }}>{m[1]}</code>;
    m = /^\[([^\]]+)\]\(([^)]*)\)$/.exec(p);
    if (m) return <a key={kb} href={m[2]} target="_blank" rel="noreferrer" style={{ color: "#1a5fa8" }}>{m[1]}</a>;
    return <span key={kb}>{p}</span>;
  });
}

function renderMarkdown(md, slots) {
  const lines = String(md ?? "").split("\n");
  const out = [];
  let i = 0, key = 0;
  const tblStyle = { width: "100%", borderCollapse: "collapse", fontSize: 11, marginTop: 6 };
  const thStyle = { background: "#f0f0f0", padding: "4px 8px", borderBottom: "1px solid #ddd", fontWeight: 600, textAlign: "left", fontSize: 11 };
  const tdStyle = { padding: "4px 8px", borderBottom: "1px solid #ececec", fontSize: 11 };
  const h2Style = { fontSize: 13, fontWeight: 700, color: "#1a5fa8", borderBottom: "2px solid #1a5fa8", paddingBottom: 4, marginBottom: 10, marginTop: 18 };
  while (i < lines.length) {
    const line = lines[i];
    const trim = line.trim();
    const slotM = /^\{\{(\w+)\}\}$/.exec(trim);
    if (slotM && slots[slotM[1]]) {
      out.push(<div key={key++} style={{ margin: "8px 0" }}>{slots[slotM[1]]}</div>);
      i += 1; continue;
    }
    if (/^###\s+/.test(trim)) {
      out.push(<h3 key={key++} style={{ fontSize: 12, fontWeight: 700, color: "#333", margin: "12px 0 6px" }}>{renderInline(trim.replace(/^###\s+/, ""), `h3-${key}`)}</h3>);
      i += 1; continue;
    }
    if (/^##\s+/.test(trim)) {
      out.push(<h2 key={key++} style={h2Style}>{renderInline(trim.replace(/^##\s+/, ""), `h2-${key}`)}</h2>);
      i += 1; continue;
    }
    if (/^---+$/.test(trim)) {
      out.push(<hr key={key++} style={{ border: "none", borderTop: "1px solid #ddd", margin: "14px 0" }} />);
      i += 1; continue;
    }
    if (/^\|\s*:?-+/.test(trim) || /^\|.*\|$/.test(trim)) {
      // table block
      const rows = [];
      while (i < lines.length && /^\|.*\|$/.test(lines[i].trim())) {
        rows.push(lines[i].trim().slice(1, -1).split("|").map(c => c.trim()));
        i += 1;
      }
      const isSep = (r) => r.every(c => /^:?-+:?$/.test(c));
      let head = null, body = rows;
      if (rows.length > 1 && isSep(rows[1])) { head = rows[0]; body = rows.slice(2); }
      out.push(
        <table key={key++} style={tblStyle}>
          {head && <thead><tr>{head.map((c, ci) => <th key={ci} style={thStyle}>{renderInline(c, `th-${key}-${ci}`)}</th>)}</tr></thead>}
          <tbody>{body.filter(r => !isSep(r)).map((r, ri) => (
            <tr key={ri}>{r.map((c, ci) => <td key={ci} style={tdStyle}>{renderInline(c, `td-${key}-${ri}-${ci}`)}</td>)}</tr>
          ))}</tbody>
        </table>
      );
      continue;
    }
    if (/^-\s+/.test(trim)) {
      const items = [];
      while (i < lines.length && /^-\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^-\s+/, ""));
        i += 1;
      }
      out.push(
        <ul key={key++} style={{ fontSize: 11, color: "#333", lineHeight: 1.8, margin: "6px 0", paddingLeft: 20 }}>
          {items.map((t, ti) => <li key={ti}>{renderInline(t, `li-${key}-${ti}`)}</li>)}
        </ul>
      );
      continue;
    }
    if (/^>\s?/.test(trim)) {
      const quotes = [];
      while (i < lines.length && /^>\s?/.test(lines[i].trim())) {
        quotes.push(lines[i].trim().replace(/^>\s?/, ""));
        i += 1;
      }
      out.push(
        <div key={key++} style={{ borderLeft: "3px solid #1a5fa8", background: "#f8fafc", padding: "6px 12px", margin: "6px 0", fontSize: 11, color: "#334155", lineHeight: 1.8 }}>
          {quotes.map((t, ti) => <div key={ti}>{renderInline(t, `q-${key}-${ti}`)}</div>)}
        </div>
      );
      continue;
    }
    if (trim === "") { i += 1; continue; }
    // paragraph (join following plain lines)
    const para = [trim];
    i += 1;
    while (i < lines.length) {
      const t2 = lines[i].trim();
      if (t2 === "" || /^(##|###|---|-\s+|>\s?|\|.*\|)$/.test(t2) || /^\{\{\w+\}\}$/.test(t2)) break;
      para.push(t2); i += 1;
    }
    out.push(<p key={key++} style={{ fontSize: 11, color: "#333", lineHeight: 1.8, margin: "6px 0" }}>{renderInline(para.join(" "), `p-${key}`)}</p>);
  }
  return out;
}

// ── Build the editable markdown source ───────────────────────────────────────
function buildMarkdown(c) {
  const compRows = Object.entries(c.composition ?? {})
    .map(([el, val]) => `| ${el} | ${Number(c.comp[el] ?? val).toFixed(1)}% | ${c.roles[el] ?? "합금 기지 원소"} |`)
    .join("\n");
  return `## 1. 합금 조성 및 원소 역할 분석

**합금 클래스**: ${c.alloyClass} / **혼합 엔트로피 ΔSmix**: ${c.Smix.toFixed(2)} J/mol·K (${c.entropyKo})

| 원소 | 정규화 (%) | 주요 역할 |
| --- | --- | --- |
${compRows}

Cr 당량(Cr_eq) **${c.phases.Cr_eq}**, Ni 당량(Ni_eq) **${c.phases.Ni_eq}** — Schaeffler 도표의 위치값이다. ΔSmix가 11 이상이면 고엔트로피 합금(HEA)으로 분류한다.

## 2. 공정 조건

| 항목 | 값 | 의미 |
| --- | --- | --- |
| 고용화 처리 온도 | ${c.solTemp} °C | 합금 원소를 고르게 녹여내기 위해 가열하는 온도 |
| 고용화 처리 시간 | ${(c.solTime / 3600).toFixed(1)} h | 균질화에 필요한 유지 시간 — 길수록 석출물 재용해 완전 |
| 시험 온도 | ${c.testTempC.toFixed(0)} °C | 시험 환경 온도 (고온일수록 강도 저하) |

조성 다음에 공정이 오는 순서다. 같은 조성이라도 용체화·냉각 조건에 따라 석출과 상분율이 달라져 뒤의 상 판정과 물성이 바뀐다.

## 3. 상 · 결정구조 판정 (Schaeffler)

**판정**: ${c.sch.zone} · ${c.sch.zoneKo} — ${c.sch.description}
**주상**: ${c.sch.dominantPhase} (${c.sch.dominantCrystal})

{{phase_bar}}

위 % 숫자의 의미: ${c.phaseMethodNote} 마르텐사이트는 평형상이 아니라 급랭 과정에서 생기는 비평형 조직이라 CALPHAD 평형 계산에는 나오지 않고 경험식에서만 추정된다. Schaeffler 도표 자체가 용접된 그대로의 조직용 경험식이라 단조·열처리재에는 참고용으로만 쓴다. WRC-1992 표준 위치값(Cr_eq ${c.phases.WRC_Cr_eq} / Ni_eq ${c.phases.WRC_Ni_eq})도 함께 기재한다. FN(페라이트수)은 도표 판독값이라 본 보고서에는 싣지 않는다.

### 결정 격자 정보 (격자 뷰어 연동)

{{lattice_info}}

{{lattice_shot}}

격자 뷰어(앱 내 팝업)에서 위 구조를 3D 단위셀로 회전·확대하며 볼 수 있다. 격자상수는 원자반지름 가중평균(Vegard 근사) 추정치이며, BCT의 c/a는 C 함량 근사식(c/a≈1+0.045·C%)을 쓴다.

## 4. 예측 물성값

| 특성 | 값 | 의미 |
| --- | --- | --- |
| 인장강도 (UTS) | **${c.UTS.toFixed(1)} MPa** | 재료가 끊어지기 직전까지 버틸 수 있는 최대 응력. 높을수록 강한 재료 |
| 항복응력 (YS) | ${c.YS.toFixed(1)} MPa | 영구 변형이 시작되는 응력. 초과하면 원래 모양으로 돌아오지 않음 |
| 탄성 계수 (E) | ${c.E.toFixed(1)} GPa | 얼마나 뻣뻣한지. 높을수록 변형이 적음 |
| 연신율 | ${c.elong?.toFixed(1) ?? "—"} % | 파단까지 늘어나는 비율. 높을수록 연성 재료 |
| 단면 감소율 (RA) | ${c.area?.toFixed(1) ?? "—"} % | 파단 후 단면적 감소율. 높을수록 에너지 흡수 능력 큼 |
| 경도 (HV / HB / HRC) | ${c.hardness.HV} / ${c.hardness.HB} / ${c.hardness.HRC} | 표면 긁힘 저항. 강도와 비례하는 경향 |
| 파괴인성 (KIC) | ${c.KIC} MPa·√m | 균열이 있어도 버티는 능력. 낮으면 작은 결함에도 갑자기 파단 |
| 밀도 | ${c.density.toFixed(2)} g/cm³ | 낮을수록 가벼운 재료 (Al ~2.7, Ti ~4.5, Fe ~7.9) |
| 용융점 | ${c.meltingPoint} °C | 녹기 시작하는 온도. 내열 용도는 높을수록 유리 |
| 열전도율 | ${c.thermalConductivity} W/m·K | 방열 부품은 높아야, 단열 부품은 낮아야 유리 |

## 5. 응력-변형률 곡선

{{ss_chart}}

가로축은 변형률(늘어난 비율 %), 세로축은 응력(MPa)이다. **주황 점선(항복점 ${c.YS.toFixed(0)} MPa)** 을 넘으면 영구 변형이 시작되고, **빨간 점선(UTS ${c.UTS.toFixed(0)} MPa)** 이 버틸 수 있는 최대 응력이다. 곡선 아래 면적은 재료가 흡수할 수 있는 에너지(인성)이며, 초기 기울기는 탄성 계수 E = ${c.E.toFixed(0)} GPa이다.

## 6. 피로 S-N 곡선 (Basquin)

{{sn_chart}}

가로축은 파단까지의 반복 횟수(로그), 세로축은 응력 진폭이다. **내구한도 약 ${c.Se.toFixed(0)} MPa** 이하에서는 사실상 무한 수명으로 본다(철강 기준). 곡선은 Basquin 식 기반 추정치라 실제 피로 시험으로 보정이 필요하다.

## 7. 3D 시뮬레이션 스냅샷

{{sim_image}}

## 8. 응력 분포 분석

| 항목 | 값 | 의미 |
| --- | --- | --- |
| 최대 등가 응력 | ${(c.simMax ?? c.UTS).toFixed(0)} MPa | 시편 내부 응력 집중점의 Von Mises 등가 응력. 3D 응력 상태를 하나의 숫자로 표현 |
| 항복 응력 (YS) | ${c.YS.toFixed(0)} MPa | 초과 시 영구 변형 |
| 안전계수 (SF) | ${typeof c.safetyFactor === "number" ? c.safetyFactor.toFixed(2) : "—"} | 항복응력 ÷ 최대응력. 1.0 미만이면 이미 소성 변형 중, 1.5 이상이면 안전한 설계 |
| 시험 방식 | ${c.activeTest === "bending" ? "굽힘" : "인장"} | ${c.activeTest === "bending" ? "굽힘: 위아래 표면 응력 최대, 중앙 중립면 0 — 표면 결함이 파단을 지배" : "인장: 게이지 중앙 응력 집중, 넥킹 시 단면 급감으로 응력 급등"} |

Von Mises 응력은 파란색(낮음)→초록→빨간색(높음) 컬러맵으로 표시된다. 안전계수는 설계 여유를 뜻한다: **1.5 이상 안전, 1.0~1.5 주의, 1.0 미만 항복 초과**로 읽는다.

## 9. 파단 분석

| 항목 | 값 | 의미 |
| --- | --- | --- |
| 파단 유형 | ${c.fracture.korean} | ${c.fracture.type === "ductile" ? "끊어지기 전에 눈에 띄게 늘어남 — 사전 경고가 있어 비교적 안전" : c.fracture.type === "brittle" ? "거의 변형 없이 갑자기 파단 — 위험, 충격에 취약" : "연성과 취성이 혼합된 중간 형태"} |
| 파면 형상 | ${c.fracture.morphology} | ${c.fracture.type === "ductile" ? "컵-앤드-콘: 중앙 섬유상 + 가장자리 45° 전단면" : "평탄한 벽개면 (cleavage)"} |
| 파단 각도 | ${c.fracture.angle}° | 최대 전단응력 방향. 45°에 가까울수록 연성, 90°면 취성 |
| 파괴인성 (KIC) | ${c.KIC} MPa·√m | 균열이 있을 때 버티는 능력 |

## 10. 예측 신뢰도

| 항목 | 값 | 의미 |
| --- | --- | --- |
| 예측 신뢰도 | ${c.confidence} % | 모델이 이 조성을 얼마나 잘 학습했는지. 90% 이상이면 신뢰도 높음 |
| 격자 안정성 | ${c.latticeStability} % | 결정 구조 유지 예측. 낮으면 상 분리·취화 위험 |
| 예측 모델 | ${c.modelSrc} | 플랫폼 모델은 실험 데이터 학습 기반, 로컬은 조성 비율 기반 추정 |
| 혼합 엔트로피 | ${c.Smix.toFixed(2)} J/mol·K | 골고루 섞일수록 높아짐. 11 이상이면 고엔트로피 합금 |

본 보고서는 디지털 트윈 시뮬레이션으로 자동 생성된 예측값이다. 실제 제조·가공 조건에 따라 결과가 달라질 수 있으며, 설계 적용 전 실측 시험을 권장한다.
`;
}

// ── Main Report Modal ─────────────────────────────────────────────────────────
export default function ReportModal({
  alloyName, composition, normalizedComposition, prediction,
  simulation, deformStats, activeTest, processParams,
  imageUrl, stressStrainPoints, onClose
}) {
  const printAreaRef = useRef(null);

  // Derived values
  const UTS  = prediction?.strengthMpa ?? 800;
  const YS   = prediction?.yieldStressMpa ?? UTS * 0.70;
  const E    = prediction?.elasticityGpa ?? 200;
  const elong = prediction?.elongationPercent ?? 15;
  const area  = prediction?.areaReductionPercent ?? 30;

  const phases    = predictPhases(composition ?? {});
  const fracture  = classifyFracture(elong, area);
  const hardness  = estimateHardness(UTS);
  const KIC       = estimateKIC(UTS, elong);
  const snCurve   = useMemo(() => generateSNCurve(UTS, YS, 16), [UTS, YS]);
  const Se        = Math.min(700, 0.504 * UTS);
  const lat       = useMemo(() => latticeEstimates(composition ?? {}), [composition]);

  // ── 파생 파라미터 ──
  const density = prediction?.density ?? 7.8;
  const solTemp = processParams?.["Solution_treatment_temperature"] ?? 1100;
  const solTime = processParams?.["Solution_treatment_time(s)"] ?? 3600;
  const testTempC = ((processParams?.["Temperature (K)"] ?? 293) - 273);
  const R = 8.314;
  const compVals = Object.values(composition ?? {});
  const total = compVals.reduce((s, v) => s + Number(v), 0) || 1;
  const Smix = -R * compVals.reduce((s, v) => {
    const x = Number(v) / total;
    return x > 0 ? s + x * Math.log(x) : s;
  }, 0);
  const compNorm = Object.fromEntries(
    Object.entries(composition ?? {}).map(([k, v]) => [k, Number(v) / total])
  );
  const dominant = Object.entries(compNorm).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "Fe";
  const alloyClass =
    dominant === "Ni" ? "니켈기 초합금" :
    dominant === "Ti" ? "타이타늄 합금" :
    dominant === "Fe" ? "철강 합금" :
    dominant === "Co" ? "코발트기 합금" :
    dominant === "Al" ? "알루미늄 합금" :
    `${dominant}기 합금`;
  const ELEMENT_ROLES = {
    Ni: "오스테나이트 안정화, 인성·내식성 향상",
    Cr: "내산화·내식성, 석출 강화",
    Ti: "석출 강화 (TiN/TiC), 결정립 미세화",
    Mo: "고용 강화, 크리프 내성",
    Al: "석출 강화 (Ni₃Al), 산화 보호막",
    Co: "고온 강도 향상",
    Fe: "기지 원소",
    Nb: "석출 강화, 결정립 고정",
    W:  "고용 강화, 크리프 저항",
    V:  "석출 강화, 결정립 미세화",
    C:  "고온 강도 (과다 시 취성 주의)",
    Cu: "석출 강화 (시효), 내식성",
    Mn: "오스테나이트 안정화, 탈산·탈황",
    Si: "산화 저항, 고용 강화",
    N:  "고용 강화, 내식성 향상",
    Zr: "결정립 고정, 산화막 안정화",
    Ta: "고온 강도, 석출 강화",
  };
  const maxBendStress = simulation?.result?.maxStressMpa ?? UTS * 0.85;
  const safetyFactor = simulation?.result?.safetyIndex ?? (YS / maxBendStress);


  const testName = {
    strength: "인장 강도 시험 (ASTM E8)",
    bending: "3점 굽힘 시험 (ASTM E290)",
    elongation: "연신율 시험",
    temperature: "고온 특성 시험 (ASTM E21)"
  }[activeTest] ?? "인장 시험";

  const today = new Date().toLocaleString("ko-KR", {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false
  });

  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");
  const [editMode, setEditMode] = useState(false);
  const [latticeShot] = useState(() => {
    try {
      const raw = localStorage.getItem("maps-lattice-shot");
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  });
  const taRef = useRef(null);

  // ── 마크다운 서식 버튼용 커서 삽입 헬퍼 ──
  const insertAtCursor = useCallback((before, after = "", placeholder = "") => {
    const ta = taRef.current;
    if (!ta) { setMdText(t => t + before + placeholder + after); return; }
    const { selectionStart: s, selectionEnd: e, value } = ta;
    const hadSel = e > s;
    const sel = hadSel ? value.slice(s, e) : placeholder;
    const next = value.slice(0, s) + before + sel + after + value.slice(e);
    setMdText(next);
    requestAnimationFrame(() => {
      ta.focus();
      if (hadSel) ta.setSelectionRange(s + before.length + sel.length + after.length, s + before.length + sel.length + after.length);
      else ta.setSelectionRange(s + before.length, s + before.length + sel.length);
    });
  }, []);
  const insertLinePrefix = useCallback((prefix) => {
    const ta = taRef.current;
    if (!ta) { setMdText(t => prefix + t); return; }
    const { selectionStart: s, value } = ta;
    const lineStart = value.lastIndexOf("\n", s - 1) + 1;
    setMdText(value.slice(0, lineStart) + prefix + value.slice(lineStart));
    requestAnimationFrame(() => {
      ta.focus();
      ta.setSelectionRange(s + prefix.length, s + prefix.length);
    });
  }, []);

  const mdCtx = {
    composition, comp: normalizedComposition ?? composition ?? {},
    roles: ELEMENT_ROLES, alloyClass, Smix,
    entropyKo: Smix > 11 ? "고엔트로피 합금 (HEA)" : Smix > 8 ? "중엔트로피 합금" : "저엔트로피 (통상 합금)",
    phases, sch: phases?.schaeffler ?? {},
    phaseMethodNote: "CALPHAD 평형 계산값이 있으면 그 값을, 없으면 Schaeffler 경험식 추정값을 표시한다. ",
    solTemp, solTime, testTempC,
    UTS, YS, E, elong, area, hardness, KIC, density,
    meltingPoint: prediction?.meltingPoint?.toFixed(0) ?? "—",
    thermalConductivity: prediction?.thermalConductivity?.toFixed(1) ?? "—",
    simMax: simulation?.result?.maxStressMpa, safetyFactor, activeTest,
    fracture,
    confidence: prediction?.predictionConfidence?.toFixed(1) ?? "—",
    latticeStability: prediction?.latticeStability?.toFixed(1) ?? "—",
    modelSrc: prediction?.predictionSource ? "플랫폼 예측 모델" : "로컬 모델",
    Se,
  };

  const initialMd = useMemo(() => buildMarkdown(mdCtx), []); // eslint-disable-line
  const [mdText, setMdText] = useState(initialMd);
  const dirty = mdText !== initialMd;

  const slots = {
    ss_chart: <ReportSSChart points={stressStrainPoints} UTS={UTS} YS={YS} elongPct={elong} />,
    sn_chart: <ReportSNChart snCurve={snCurve} Se={Se} />,
    phase_bar: <PhaseBar phases={phases} />,
    lattice_info: (
      <div>        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11, marginTop: 6 }}>
          <thead><tr>
            {[ "구조", "격자상수 (추정)", "대응 상" ].map((h, i) => (
              <th key={i} style={{ background: "#f0f0f0", padding: "4px 8px", borderBottom: "1px solid #ddd", fontWeight: 600, textAlign: "left", fontSize: 11 }}>{h}</th>
            ))}
          </tr></thead>
          <tbody>
            <tr>
              <td style={{ padding: "4px 8px", borderBottom: "1px solid #ececec", fontSize: 11 }}>FCC (면심입방)</td>
              <td style={{ padding: "4px 8px", borderBottom: "1px solid #ececec", fontSize: 11 }}>a = {lat.aFcc !== null ? lat.aFcc.toFixed(2) : "—"} Å</td>
              <td style={{ padding: "4px 8px", borderBottom: "1px solid #ececec", fontSize: 11 }}>γ 오스테나이트</td>
            </tr>
            <tr>
              <td style={{ padding: "4px 8px", borderBottom: "1px solid #ececec", fontSize: 11 }}>BCC (체심입방)</td>
              <td style={{ padding: "4px 8px", borderBottom: "1px solid #ececec", fontSize: 11 }}>a = {lat.aBcc !== null ? lat.aBcc.toFixed(2) : "—"} Å</td>
              <td style={{ padding: "4px 8px", borderBottom: "1px solid #ececec", fontSize: 11 }}>α 페라이트</td>
            </tr>
            <tr>
              <td style={{ padding: "4px 8px", borderBottom: "1px solid #ececec", fontSize: 11 }}>BCT (체심정방)</td>
              <td style={{ padding: "4px 8px", borderBottom: "1px solid #ececec", fontSize: 11 }}>a = {lat.aBcc !== null ? lat.aBcc.toFixed(2) : "—"} Å, c = {lat.cBct !== null ? lat.cBct.toFixed(2) : "—"} Å (c/a={lat.cOverA.toFixed(3)})</td>
              <td style={{ padding: "4px 8px", borderBottom: "1px solid #ececec", fontSize: 11 }}>α' 마르텐사이트</td>
            </tr>
          </tbody>
        </table>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 12px", marginTop: 6 }}>
          {lat.legend.map(l => (
            <span key={l.el} style={{ fontSize: 10, color: "#444", display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: l.color, display: "inline-block" }} />
              {l.el}: <strong>{l.pct}%</strong>
            </span>
          ))}
        </div>
      </div>
    ),
    lattice_shot: latticeShot?.img ? (
      <div>
        <img src={latticeShot.img} alt="격자 뷰어 스냅샷"
          style={{ width: 320, borderRadius: 4, border: "1px solid #ddd" }} />
        <div style={{ fontSize: 10, color: "#888", marginTop: 4 }}>
          격자 뷰어 스냅샷 ({latticeShot.structure})
        </div>
      </div>
    ) : (
      <div style={{ fontSize: 11, color: "#999", padding: 12, background: "#f8f8f8",
        borderRadius: 4, textAlign: "center" }}>
        격자 뷰어에서 📷 스냅샷을 저장한 뒤 보고서를 다시 열면 사진이 들어갑니다.
      </div>
    ),
    sim_image: imageUrl ? (
      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
        <img src={imageUrl} alt="3D Simulation" style={{ width: 340, borderRadius: 4, border: "1px solid #ddd" }} />
        <div style={{ fontSize: 11, color: "#555", lineHeight: 1.8 }}>
          <div><strong>시험 종류:</strong> {testName}</div>
          <div><strong>최대 변형률:</strong> {(deformStats?.maxStrain ?? 0).toFixed(1)}%</div>
          <div><strong>재료 상태:</strong> {(deformStats?.maxStrain ?? 0) < 2 ? "탄성" : (deformStats?.maxStrain ?? 0) < 8 ? "소성 변형" : "파단"}</div>
          {simulation?.result && <>
            <div><strong>최대 응력:</strong> {simulation.result.maxStressMpa?.toFixed(0)} MPa</div>
            <div><strong>파손 위험:</strong> {simulation.result.failureRisk}</div>
            <div><strong>안전 지수:</strong> {simulation.result.safetyIndex?.toFixed(1)}</div>
          </>}
        </div>
      </div>
    ) : (
      <div style={{ fontSize: 11, color: "#999", padding: 16, background: "#f8f8f8", borderRadius: 4, textAlign: "center" }}>
        시뮬레이션 실행 후 보고서를 다시 생성하면 이미지가 포함됩니다.
      </div>
    ),
  };

  const rendered = useMemo(() => renderMarkdown(mdText, slots), [mdText]); // eslint-disable-line

  const handlePrint = useCallback(async () => {
    if (window.desktopApi?.savePDF) {
      setSaving(true);
      setSaveMsg("");
      try {
        // Serialize only the report content (white bg, no 3D canvas/dark theme)
        const contentHtml = printAreaRef.current?.innerHTML ?? "";
        const result = await window.desktopApi.savePDF({ contentHtml });
        if (result?.success) {
          setSaveMsg(`저장 완료: ${result.filePath?.split(/[\\/]/).pop() ?? "파일"}`);
        } else if (!result?.canceled) {
          setSaveMsg("저장 실패");
        }
      } catch (e) {
        setSaveMsg("저장 오류: " + (e?.message ?? "unknown"));
      } finally {
        setSaving(false);
      }
    } else {
      window.print();
    }
  }, []);

  // ESC to close
  useEffect(() => {
    const fn = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, [onClose]);

  const comp = normalizedComposition ?? composition ?? {};
  void comp;

  return createPortal(
    <>
      {/* ── Backdrop ── */}
      <div
        className="report-backdrop"
        onClick={onClose}
        style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)",
          zIndex: 2000, display: "flex", alignItems: "flex-start",
          justifyContent: "center", overflowY: "auto", padding: "24px 16px"
        }}
      >
        {/* ── Modal Box ── */}
        <div
          className="report-modal"
          onClick={e => e.stopPropagation()}
          style={{
            background: "#fff", borderRadius: 6, width: editMode ? 1180 : 820,
            maxWidth: "100%", boxShadow: "0 8px 40px rgba(0,0,0,0.25)",
            fontFamily: "'IBM Plex Sans','Noto Sans KR',sans-serif",
            color: "#1e1e1e"
          }}
        >
          {/* ── Toolbar ── */}
          <div style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "12px 20px", background: "#1a5fa8", borderRadius: "6px 6px 0 0"
          }}>
            <span style={{ color: "#fff", fontWeight: 700, fontSize: 14 }}>
              ⚗ 재료 시험 보고서{dirty ? " (수정됨)" : ""}
            </span>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {saveMsg && (
                <span style={{ fontSize: 11, color: saveMsg.includes("완료") ? "#afffb5" : "#ffb3b3" }}>
                  {saveMsg}
                </span>
              )}
              <button
                onClick={() => setEditMode(v => !v)}
                style={{
                  background: editMode ? "#FFB020" : "rgba(255,255,255,0.2)", color: editMode ? "#1e1e1e" : "#fff",
                  border: "1px solid rgba(255,255,255,0.4)",
                  borderRadius: 4, padding: "5px 14px", fontWeight: 700,
                  fontSize: 12, cursor: "pointer"
                }}
              >
                {editMode ? "✓ 편집 완료" : "✎ 편집"}
              </button>
              {editMode && dirty && (
                <button
                  onClick={() => setMdText(initialMd)}
                  style={{
                    background: "rgba(255,255,255,0.2)", color: "#fff",
                    border: "1px solid rgba(255,255,255,0.4)",
                    borderRadius: 4, padding: "5px 10px", cursor: "pointer", fontSize: 12
                  }}
                >
                  초기화
                </button>
              )}
              <button
                onClick={handlePrint}
                disabled={saving}
                style={{
                  background: "#fff", color: "#1a5fa8", border: "none",
                  borderRadius: 4, padding: "5px 14px", fontWeight: 700,
                  fontSize: 12, cursor: saving ? "not-allowed" : "pointer",
                  opacity: saving ? 0.7 : 1
                }}
              >
                {saving ? "저장 중..." : "💾 PDF 저장"}
              </button>
              <button
                onClick={onClose}
                style={{
                  background: "rgba(255,255,255,0.2)", color: "#fff",
                  border: "1px solid rgba(255,255,255,0.4)",
                  borderRadius: 4, padding: "5px 10px", cursor: "pointer", fontSize: 12
                }}
              >
                ✕ 닫기
              </button>
            </div>
          </div>

          {/* ── Print Area (single source of truth for PDF) ── */}
          {editMode ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0 }}>
              <div style={{ borderRight: "1px solid #ddd", display: "flex", flexDirection: "column" }}>
                <div style={{ padding: "8px 14px", background: "#f1f5f9", fontSize: 11, fontWeight: 700, color: "#475569" }}>
                  Markdown 편집
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4, padding: "6px 10px", background: "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>
                  {[
                    { label: "굵게", title: "선택 영역 굵게 (**)", fn: () => insertAtCursor("**", "**", "굵은 글씨") },
                    { label: "제목", title: "줄을 ## 제목으로", fn: () => insertLinePrefix("## ") },
                    { label: "소제목", title: "줄을 ### 소제목으로", fn: () => insertLinePrefix("### ") },
                    { label: "목록", title: "줄을 글머리(- )로", fn: () => insertLinePrefix("- ") },
                    { label: "표", title: "3열 표 골격 삽입", fn: () => insertAtCursor("\n| 항목 | 값 | 의미 |\n| --- | --- | --- |\n|  |  |  |\n") },
                    { label: "구분선", title: "--- 삽입", fn: () => insertAtCursor("\n---\n") },
                    { label: "A- 작게", title: "선택 영역 10px (@10())", fn: () => insertAtCursor("@10(", ")", "작은 글씨") },
                    { label: "A 보통", title: "선택 영역 12px (@12())", fn: () => insertAtCursor("@12(", ")", "보통 글씨") },
                    { label: "A+ 크게", title: "선택 영역 15px (@15())", fn: () => insertAtCursor("@15(", ")", "큰 글씨") },
                    { label: "인용", title: "줄을 인용(> )으로", fn: () => insertLinePrefix("> ") },
                    { label: "코드", title: "선택 영역 코드(`)", fn: () => insertAtCursor("`", "`", "코드") },
                    { label: "링크", title: "선택 영역 링크([텍스트](url))", fn: () => insertAtCursor("[", "](https://)", "링크 텍스트") },
                    { label: "응력곡선", title: "{{ss_chart}} 삽입", fn: () => insertAtCursor("\n{{ss_chart}}\n") },
                    { label: "S-N곡선", title: "{{sn_chart}} 삽입", fn: () => insertAtCursor("\n{{sn_chart}}\n") },
                    { label: "상분율", title: "{{phase_bar}} 삽입", fn: () => insertAtCursor("\n{{phase_bar}}\n") },
                    { label: "스냅샷", title: "{{sim_image}} 삽입", fn: () => insertAtCursor("\n{{sim_image}}\n") },
                  ].map(b => (
                    <button key={b.label} onClick={b.fn} title={b.title}
                      style={{ padding: "3px 9px", fontSize: 11, fontWeight: 600, background: "#fff", color: "#334155", border: "1px solid #cbd5e1", borderRadius: 4, cursor: "pointer" }}>
                      {b.label}
                    </button>
                  ))}
                </div>
                <textarea
                  ref={taRef}
                  value={mdText}
                  onChange={e => setMdText(e.target.value)}
                  spellCheck={false}
                  style={{
                    flex: 1, minHeight: 600, border: "none", outline: "none",
                    padding: "14px", fontSize: 12, lineHeight: 1.7,
                    fontFamily: "'Consolas','D2Coding',monospace", resize: "vertical"
                  }}
                />
              </div>
              <div ref={printAreaRef} className="report-print-area" style={{ padding: "24px 28px" }}>
                <div style={{ textAlign: "center", marginBottom: 18, borderBottom: "1px solid #ddd", paddingBottom: 14 }}>
                  <div style={{ fontSize: 20, fontWeight: 800, color: "#1a5fa8", letterSpacing: -0.5 }}>
                    합금 디지털 트윈 — 재료 시험 보고서
                  </div>
                  <div style={{ fontSize: 12, color: "#555", marginTop: 4 }}>
                    합금: <strong>{alloyName ?? "—"}</strong> &nbsp;·&nbsp; 시험: <strong>{testName}</strong>
                    &nbsp;·&nbsp; 발행일: {today}
                  </div>
                </div>
                {rendered}
              </div>
            </div>
          ) : (
            <div
              ref={printAreaRef}
              className="report-print-area"
              style={{ padding: "24px 28px" }}
            >
              <div style={{ textAlign: "center", marginBottom: 18, borderBottom: "1px solid #ddd", paddingBottom: 14 }}>
                <div style={{ fontSize: 20, fontWeight: 800, color: "#1a5fa8", letterSpacing: -0.5 }}>
                  합금 디지털 트윈 — 재료 시험 보고서
                </div>
                <div style={{ fontSize: 12, color: "#555", marginTop: 4 }}>
                  합금: <strong>{alloyName ?? "—"}</strong> &nbsp;·&nbsp; 시험: <strong>{testName}</strong>
                  &nbsp;·&nbsp; 발행일: {today}
                </div>
              </div>
              {rendered}
            </div>
          )}
        </div>
      </div>
    </>,
    document.body
  );
}
