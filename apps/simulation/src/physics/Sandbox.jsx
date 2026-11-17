// 충돌 샌드박스(개발용 단독 화면): 프리셋 재료 + 조성을 적어 MAPS 예측을 받아 쓰는 입력. 화면 본체는 CrashLab.jsx.
import React, { useState } from "react";
import CrashLab from "./CrashLab.jsx";

const PRESETS = {
  ductile: { label: "연성 강 (304 계열)", yieldStressMpa: 280, strengthMpa: 620, elongationPercent: 45, elasticityGpa: 193, density: 7.9 },
  mid:     { label: "중간 (고강도 강)",   yieldStressMpa: 450, strengthMpa: 700, elongationPercent: 18, elasticityGpa: 200, density: 7.8 },
  brittle: { label: "취성 (연신율 3%)",   yieldStressMpa: 900, strengthMpa: 1000, elongationPercent: 3, elasticityGpa: 200, density: 7.8 },
};
// 시뮬 앱(App.jsx)과 같은 백엔드·같은 공정 조건 (용체화 1050 °C · 1시간, 상온 시험)
const BACKEND = "http://127.0.0.1:8765";
const PROCESS = { "Solution_treatment_temperature": 1050 + 273.15, "Solution_treatment_time(s)": 3600, "Temperature (K)": 293 };

// "Fe 70, Cr 18, Ni 9" → { Fe: 70, Cr: 18, Ni: 9 }
function parseComposition(text) {
  const out = {};
  for (const m of text.matchAll(/([A-Z][a-z]?)\s*:?\s*(\d+(?:\.\d+)?)/g)) out[m[1]] = Number(m[2]);
  return out;
}

export default function Sandbox() {
  const [materials, setMaterials] = useState(PRESETS);
  const [compText, setCompText] = useState("Fe 70, Cr 18, Ni 9, Mn 1.5, C 0.05");
  const [fetchState, setFetchState] = useState("");

  async function fetchPrediction() {
    const composition = parseComposition(compText);
    if (!Object.keys(composition).length) { setFetchState("조성을 '원소 함량' 형식으로 적어 주세요 (예: Fe 70, Cr 18, Ni 9)"); return; }
    setFetchState("예측 중…");
    try {
      const res = await fetch(`${BACKEND}/predict`, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ composition, densityScale: 0.6, process: PROCESS }) });
      if (!res.ok) throw new Error(String(res.status));
      const r = await res.json();
      const label = `MAPS 예측 · ${Object.entries(composition).map(([el, v]) => `${el}${v}`).join(" ")}`;
      setMaterials((m) => ({ ...m, maps: { label, yieldStressMpa: r.yieldStressMpa, strengthMpa: r.strengthMpa, elongationPercent: r.elongationPercent,
        elasticityGpa: r.elasticityGpa, density: r.density } }));
      setFetchState("재료 목록에 추가했습니다.");
    } catch {
      setFetchState("시뮬 백엔드(127.0.0.1:8765)에 연결하지 못했습니다. 백엔드를 켠 뒤 다시 눌러 주세요.");
    }
  }

  return (
    <CrashLab materials={materials}>
      <form className="sb-maps" onSubmit={(e) => { e.preventDefault(); fetchPrediction(); }}>
        <label htmlFor="sb-comp">MAPS 모델로 예측 (조성, wt%)</label>
        <input id="sb-comp" type="text" value={compText} onChange={(e) => setCompText(e.target.value)} spellCheck="false" />
        <button type="submit" className="sb-btn">물성 예측 받기</button>
        {fetchState && <p className="sb-note" role="status">{fetchState}</p>}
      </form>
    </CrashLab>
  );
}
