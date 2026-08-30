import type { Rung } from "@/lib/types";
import { f3, signed } from "@/lib/fmt";

/**
 * The thesis in one chart: each bar is a shortcut removed, and its drop is that
 * shortcut's contribution to the inflated headline. Bars are labelled with their
 * own delta, so the chart is readable in grayscale and without the legend.
 */
export function Waterfall({ rungs }: { rungs: Rung[] }) {
  const W = 720, H = 320, ML = 52, MR = 16, MT = 24, MB = 78;
  const iw = W - ML - MR, ih = H - MT - MB;
  const vals = rungs.map((r) => r.sharpe);
  const hi = Math.max(...vals, 0.05), lo = Math.min(...vals, 0);
  const pad = (hi - lo) * 0.15 || 0.1;
  const yMax = hi + pad, yMin = lo - pad;
  const y = (v: number) => MT + ih - ((v - yMin) / (yMax - yMin)) * ih;
  const bw = (iw / rungs.length) * 0.56;
  const cx = (i: number) => ML + (iw / rungs.length) * (i + 0.5);

  const ticks = 5;
  const tickVals = Array.from({ length: ticks }, (_, i) => yMin + ((yMax - yMin) * i) / (ticks - 1));

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img"
      aria-label="Sharpe ratio at each rung of the bias ladder">
      {tickVals.map((t, i) => (
        <g key={i}>
          <line x1={ML} x2={W - MR} y1={y(t)} y2={y(t)} className="axis" opacity={0.55} />
          <text x={ML - 8} y={y(t) + 3.5} textAnchor="end" className="val">{t.toFixed(2)}</text>
        </g>
      ))}
      <line x1={ML} x2={W - MR} y1={y(0)} y2={y(0)} className="zero" />

      {rungs.map((r, i) => {
        const top = Math.min(y(r.sharpe), y(0));
        const h = Math.abs(y(r.sharpe) - y(0));
        const fill = i === 0 ? "var(--d-blue)" : r.sharpe >= 0 ? "var(--d-green)" : "var(--d-vermillion)";
        return (
          <g key={r.rung}>
            {i > 0 && (
              <line x1={cx(i - 1)} x2={cx(i)} y1={y(rungs[i - 1]!.sharpe)} y2={y(rungs[i - 1]!.sharpe)}
                stroke="var(--rule-strong)" strokeDasharray="2 3" />
            )}
            <rect x={cx(i) - bw / 2} y={top} width={bw} height={Math.max(h, 1.5)}
              fill={fill} opacity={i === 0 ? 0.95 : 0.85} rx={1.5} />
            <text x={cx(i)} y={top - 7} textAnchor="middle" className="val"
              style={{ fill: "var(--ink)", fontWeight: 600, fontSize: 12 }}>
              {f3(r.sharpe)}
            </text>
            {i > 0 && (
              <text x={cx(i)} y={y(0) + (r.sharpe >= 0 ? 16 : -6) + (r.sharpe >= 0 ? h : 0) * 0} textAnchor="middle"
                className="val" style={{ fill: r.delta < 0 ? "var(--d-vermillion)" : "var(--d-green)", fontSize: 11 }}
                dy={r.sharpe >= 0 ? 0 : 0}>
                {signed(r.delta)}
              </text>
            )}
            <text x={cx(i)} y={H - MB + 34} textAnchor="middle"
              style={{ fill: "var(--ink-2)", fontWeight: 600, fontSize: 12 }}>{r.rung}</text>
            <text x={cx(i)} y={H - MB + 50} textAnchor="middle" style={{ fontSize: 10.5 }}>
              {r.label.replace(/^\+ /, "")}
            </text>
          </g>
        );
      })}
      <text x={ML - 40} y={MT + ih / 2} transform={`rotate(-90 ${ML - 40} ${MT + ih / 2})`}
        textAnchor="middle" style={{ fontSize: 11 }}>Sharpe (annualized)</text>
    </svg>
  );
}
