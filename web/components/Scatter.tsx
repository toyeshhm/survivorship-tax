import { f2 } from "@/lib/fmt";

/**
 * In-sample against out-of-sample Sharpe for the configuration that won each CSCV
 * split. A negative slope means the parameter search is selecting noise: the better
 * a configuration looked in-sample, the worse it did out of sample.
 */
export function Scatter({
  points, slope, pbo,
}: { points: { is: number; oos: number }[]; slope: number | null; pbo: number | null }) {
  const W = 360, H = 300, ML = 44, MR = 12, MT = 14, MB = 40;
  const iw = W - ML - MR, ih = H - MT - MB;
  const xs = points.map((p) => p.is), ys = points.map((p) => p.oos);
  const xLo = Math.min(...xs), xHi = Math.max(...xs);
  const yLo = Math.min(...ys), yHi = Math.max(...ys);
  const x = (v: number) => ML + ((v - xLo) / (xHi - xLo || 1)) * iw;
  const y = (v: number) => MT + ih - ((v - yLo) / (yHi - yLo || 1)) * ih;

  const mx = xs.reduce((a, b) => a + b, 0) / xs.length;
  const my = ys.reduce((a, b) => a + b, 0) / ys.length;
  const s = slope ?? 0;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img"
      aria-label="In-sample versus out-of-sample Sharpe of selected configurations">
      <line x1={ML} x2={W - MR} y1={y(0)} y2={y(0)} className="zero" />
      <line x1={x(0)} x2={x(0)} y1={MT} y2={MT + ih} className="axis" />
      {points.map((p, i) => (
        <circle key={i} cx={x(p.is)} cy={y(p.oos)} r={2.1} fill="var(--d-blue)" opacity={0.32} />
      ))}
      <line x1={x(xLo)} y1={y(my + s * (xLo - mx))} x2={x(xHi)} y2={y(my + s * (xHi - mx))}
        stroke="var(--d-vermillion)" strokeWidth={2} />
      <text x={ML + 10} y={MT + 12} style={{ fill: "var(--ink)", fontSize: 11.5, fontWeight: 600 }}>
        slope {f2(slope)} · PBO {f2(pbo)}
      </text>
      <text x={ML + iw / 2} y={H - 8} textAnchor="middle" style={{ fontSize: 11 }}>
        in-sample Sharpe
      </text>
      <text x={ML - 32} y={MT + ih / 2} transform={`rotate(-90 ${ML - 32} ${MT + ih / 2})`}
        textAnchor="middle" style={{ fontSize: 11 }}>out-of-sample Sharpe</text>
    </svg>
  );
}
