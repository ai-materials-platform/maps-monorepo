import React, { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

// 원소 색 — 인접 원소끼리 확실히 구분되도록 고대비 팔레트
const ELEMENT_COLORS = {
  Fe: "#EF4444", Cr: "#3B82F6", Ni: "#22C55E", Mo: "#A855F7",
  Mn: "#EAB308", Si: "#EC4899", C: "#111827", N: "#06B6D4",
  Al: "#E5E7EB", Ti: "#0F766E", Co: "#F97316", Cu: "#B87333",
  Nb: "#14B8A6", W: "#6B7280", V: "#C026D3", Mg: "#FDE68A",
  Zn: "#7D80B0", Zr: "#94E0E0", Ta: "#4C6FEF",
};
// 금속 반지름 (Å, Vegard 근사용)
const METALLIC_R = {
  Fe: 1.26, Cr: 1.28, Ni: 1.24, Mo: 1.39, Mn: 1.27, Si: 1.17,
  C: 0.77, N: 0.75, Al: 1.43, Ti: 1.47, Co: 1.25, Cu: 1.28,
  Nb: 1.46, W: 1.39, V: 1.34, Mg: 1.60, Zr: 1.60, Ta: 1.46,
};

function colorFor(el) {
  if (ELEMENT_COLORS[el]) return ELEMENT_COLORS[el];
  let h = 0;
  for (const ch of el) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return `hsl(${h},55%,60%)`;
}

// 격자상수 추정치 (Vegard 근사) — 보고서에서도 재사용
export function latticeEstimates(composition) {
  const entries = Object.entries(composition ?? {})
    .map(([el, v]) => [el, Number(v) || 0]).filter(([, v]) => v > 0);
  const total = entries.reduce((s, [, v]) => s + v, 0) || 1;
  let r = 0, wsum = 0;
  for (const [el, v] of entries) {
    const ri = METALLIC_R[el];
    if (ri === undefined) continue;
    r += (v / total) * ri; wsum += v / total;
  }
  const legend = entries
    .sort((a, b) => b[1] - a[1])
    .map(([el, v]) => ({ el, pct: ((v / total) * 100).toFixed(1), color: colorFor(el) }));
  if (wsum <= 0) return { aFcc: null, aBcc: null, cBct: null, cOverA: 1, legend };
  r = r / wsum;
  const aFcc = 2 * Math.SQRT2 * r;
  const aBcc = (4 * r) / Math.sqrt(3);
  const cPct = Number(composition?.C ?? 0);
  const cOverA = Math.min(1.15, 1 + 0.045 * Math.max(0, cPct));
  return { aFcc, aBcc, cBct: aBcc * cOverA, cOverA, legend };
}

// 단위셀 원자 자리 (단위: 격자상수 a=1, 중심 원점)
function cellSites(structure) {
  const c = [-0.5, 0.5];
  const corners = [];
  for (const x of c) for (const y of c) for (const z of c) corners.push([x, y, z]);
  if (structure === "FCC") {
    return [...corners,
      [0, 0, 0.5], [0, 0, -0.5], [0, 0.5, 0], [0, -0.5, 0], [0.5, 0, 0], [-0.5, 0, 0]];
  }
  // BCC / BCT: 모서리 + 체심
  return [...corners, [0, 0, 0]];
}

// 조성 비율대로 자리 배정 (결정적 탐욕 배분)
function assignElements(sites, composition) {
  const entries = Object.entries(composition ?? {})
    .map(([el, v]) => [el, Number(v) || 0])
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1]);
  if (!entries.length) return sites.map(() => "Fe");
  const total = entries.reduce((s, [, v]) => s + v, 0) || 1;
  const quota = entries.map(([el, v]) => [el, (v / total) * sites.length]);
  return sites.map((_, i) => {
    let best = 0;
    for (let k = 1; k < quota.length; k++) {
      if (quota[k][1] > quota[best][1]) best = k;
    }
    quota[best][1] -= 1;
    return quota[best][0];
  });
}

function CameraControls() {
  const { camera, gl } = useThree();
  const ref = useRef();
  useEffect(() => {
    const ctrl = new OrbitControls(camera, gl.domElement);
    ctrl.enableDamping = true;
    ctrl.dampingFactor = 0.1;
    ctrl.minDistance = 2;
    ctrl.maxDistance = 20;
    ref.current = ctrl;
    return () => ctrl.dispose();
  }, [camera, gl]);
  useFrame(() => ref.current?.update());
  return null;
}

function CellFrame({ a, cOverA }) {
  const A = 2, C = 2 * cOverA;
  const edges = useMemo(() => {
    const x = A / 2, y = A / 2, z = C / 2;
    const P = [];
    for (const sx of [-x, x]) for (const sy of [-y, y]) {
      P.push([[sx, sy, -z], [sx, sy, z]]);
    }
    for (const sz of [-z, z]) for (const sy of [-y, y]) {
      P.push([[-x, sy, sz], [x, sy, sz]]);
    }
    for (const sz of [-z, z]) for (const sx of [-x, x]) {
      P.push([[sx, -y, sz], [sx, y, sz]]);
    }
    return P;
  }, [A, C]);
  return (
    <group>
      {edges.map(([p1, p2], i) => {
        const mid = [(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2, (p1[2] + p2[2]) / 2];
        const len = Math.hypot(p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]);
        // cylinder 기본 축 = Y. X방향 변은 Z회전, Z방향 변은 X회전, Y방향 변은 그대로
        const alongX = p1[1] === p2[1] && p1[2] === p2[2];
        const alongZ = p1[0] === p2[0] && p1[1] === p2[1];
        const rot = alongX ? [0, 0, Math.PI / 2] : alongZ ? [Math.PI / 2, 0, 0] : [0, 0, 0];
        return (
          <mesh key={i} position={mid} rotation={rot}>
            <cylinderGeometry args={[0.02, 0.02, len, 8]} />
            <meshStandardMaterial color="#94a3b8" transparent opacity={0.55} />
          </mesh>
        );
      })}
    </group>
  );
}

function Atoms({ sites, elements, cOverA, atomR }) {
  return (
    <group>
      {sites.map((s, i) => (
        <mesh key={i} position={[s[0] * 2, s[1] * 2, s[2] * 2 * cOverA]}>
          <sphereGeometry args={[atomR, 24, 24]} />
          <meshStandardMaterial color={colorFor(elements[i])} roughness={0.35} metalness={0.55} />
        </mesh>
      ))}
    </group>
  );
}

function Replicated({ structure, composition, repeat, cOverA }) {
  const base = useMemo(() => cellSites(structure), [structure]);
  const { sites, elements } = useMemo(() => {
    const all = [];
    for (let ix = 0; ix < repeat; ix++)
      for (let iy = 0; iy < repeat; iy++)
        for (let iz = 0; iz < repeat; iz++)
          for (const s of base) all.push([s[0] + ix - (repeat - 1) / 2, s[1] + iy - (repeat - 1) / 2, s[2] + iz - (repeat - 1) / 2]);
    return { sites: all, elements: assignElements(all, composition) };
  }, [base, composition, repeat]);
  return (
    <group>
      <CellFrame a={2} cOverA={cOverA} />
      <Atoms sites={sites} elements={elements} cOverA={cOverA} atomR={0.52} />
    </group>
  );
}

const STRUCT_INFO = {
  FCC: { label: "FCC (면심입방)", origin: "γ 오스테나이트" },
  BCC: { label: "BCC (체심입방)", origin: "α 페라이트" },
  BCT: { label: "BCT (체심정방)", origin: "α' 마르텐사이트" },
};

export default function LatticeViewer({ composition, dominantPhase, dominantCrystal, onClose }) {
  const auto = dominantCrystal === "BCC" ? "BCC" : dominantCrystal === "BCT" ? "BCT" : "FCC";
  const [structure, setStructure] = useState(auto);
  const [repeat, setRepeat] = useState(1);
  const [shotMsg, setShotMsg] = useState("");
  const glRef = useRef(null);

  function saveSnapshot() {
    try {
      const url = glRef.current?.domElement?.toDataURL("image/png");
      if (!url) { setShotMsg("실패"); return; }
      localStorage.setItem("maps-lattice-shot", JSON.stringify({
        img: url, structure, at: new Date().toISOString(),
      }));
      setShotMsg("✓ 저장됨");
    } catch {
      setShotMsg("실패");
    }
  }

  const est = useMemo(() => latticeEstimates(composition), [composition]);
  const { aLabel, cLabel } = useMemo(() => {
    if (est.aFcc === null) return { aLabel: "—", cLabel: null };
    if (structure === "FCC") return { aLabel: `a = ${est.aFcc.toFixed(2)} Å (추정)`, cLabel: null };
    if (structure === "BCT") return { aLabel: `a = ${est.aBcc.toFixed(2)} Å (추정)`, cLabel: `c = ${est.cBct.toFixed(2)} Å (c/a=${est.cOverA.toFixed(3)}, C기반 추정)` };
    return { aLabel: `a = ${est.aBcc.toFixed(2)} Å (추정)`, cLabel: null };
  }, [est, structure]);

  const cOverA = structure === "BCT" ? est.cOverA : 1;

  const legend = est.legend;

  return (
    <div onClick={onClose}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 3200, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
      <div onClick={e => e.stopPropagation()}
        style={{ background: "#0B1020", borderRadius: 10, width: 760, maxWidth: "100%", color: "#e2e8f0", boxShadow: "0 8px 40px rgba(0,0,0,0.4)", fontFamily: "'IBM Plex Sans','Noto Sans KR',sans-serif" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.12)" }}>
          <strong style={{ fontSize: 14 }}>결정 격자 뷰어</strong>
          <span style={{ fontSize: 11, color: "#94a3b8" }}>{STRUCT_INFO[structure].label} · {STRUCT_INFO[structure].origin} · 주상 {dominantPhase ?? "-"}</span>
          <div style={{ flex: 1 }} />
          {["FCC", "BCC", "BCT"].map(s => (
            <button key={s} onClick={() => setStructure(s)}
              style={{ padding: "4px 10px", fontSize: 11, fontWeight: 700, borderRadius: 6, cursor: "pointer", border: structure === s ? "none" : "1px solid rgba(255,255,255,0.2)", background: structure === s ? "#3b82f6" : "transparent", color: structure === s ? "#fff" : "#94a3b8" }}>
              {s}
            </button>
          ))}
          <button onClick={() => setRepeat(r => (r === 1 ? 2 : 1))}
            style={{ padding: "4px 10px", fontSize: 11, fontWeight: 700, borderRadius: 6, cursor: "pointer", border: "1px solid rgba(255,255,255,0.2)", background: "transparent", color: "#94a3b8" }}>
            {repeat === 1 ? "2×2×2" : "1×1×1"}
          </button>
          <button onClick={saveSnapshot} title="지금 화면을 보고서용으로 저장"
            style={{ padding: "4px 10px", fontSize: 11, fontWeight: 700, borderRadius: 6, cursor: "pointer", border: "1px solid rgba(255,255,255,0.2)", background: "transparent", color: "#94a3b8" }}>
            {shotMsg || "저장"}
          </button>
          <button onClick={onClose}
            style={{ padding: "4px 10px", fontSize: 12, borderRadius: 6, cursor: "pointer", border: "1px solid rgba(255,255,255,0.2)", background: "transparent", color: "#94a3b8" }}>
            ✕ 닫기
          </button>
        </div>
        <div style={{ display: "flex", gap: 0 }}>
          <div style={{ width: 480, height: 420 }}>
            <Canvas camera={{ position: [4.2, 3.2, 5.2], fov: 45 }} dpr={[1, 2]}
              gl={{ preserveDrawingBuffer: true }}
              onCreated={({ gl }) => { glRef.current = gl; }}>
              <color attach="background" args={["#0B1020"]} />
              <ambientLight intensity={0.55} />
              <directionalLight position={[6, 8, 6]} intensity={2.2} />
              <directionalLight position={[-5, -3, -4]} intensity={0.7} />
              <CameraControls />
              <Replicated structure={structure} composition={composition} repeat={repeat} cOverA={cOverA} />
            </Canvas>
          </div>
          <div style={{ flex: 1, padding: "14px 16px", borderLeft: "1px solid rgba(255,255,255,0.12)", fontSize: 12, lineHeight: 1.8 }}>
            <div style={{ fontWeight: 700, marginBottom: 6, color: "#7EC8E3" }}>격자 정보 (Vegard 근사 추정치)</div>
            <div>{aLabel}</div>
            {cLabel && <div>{cLabel}</div>}
            <div style={{ fontWeight: 700, margin: "10px 0 6px", color: "#7EC8E3" }}>원소 범례</div>
            {legend.map(l => (
              <div key={l.el} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 10, height: 10, borderRadius: "50%", background: l.color, display: "inline-block" }} />
                <span style={{ fontFamily: "monospace" }}>{l.el} {l.pct}%</span>
              </div>
            ))}
            <div style={{ marginTop: 10, fontSize: 10, color: "#64748b", lineHeight: 1.6 }}>
              드래그 회전 · 휠 줌. 격자상수는 원자반지름 가중평균(Vegard)으로 추정한 참고값이며, BCT의 c/a는 C 함량 근사식(c/a≈1+0.045·C%)을 쓴다.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
