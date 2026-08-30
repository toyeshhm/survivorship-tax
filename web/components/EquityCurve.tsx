import type { Curve } from "@/lib/types";
import { year } from "@/lib/fmt";

/**
 * Log-scale wealth, naive against honest, with the pre-registered holdout shaded.
 * The drawdown panel shares the x-axis so peaks and troughs line up vertically.
 */
export function EquityCurve({ curve }: { curve: Curve }) {
  const W = 720, ML = 54, MR = 14, MT = 18;
  const HE = 236, HD = 96, GAP = 6;
  const H = MT + HE + GAP + HD + 34;
  const iw = W - ML - MR;

  const n = curve.dates.length;
  const all = [...curve.naive, ...curve.honest].filter((v) => v > 0);
  const lo = Math.min(...all), hi = Math.max(...all);
  const lg = (v: number) => Math.log(Math.max(v, 1e-6));
  const yE = (v: number) => MT + HE - ((lg(v) - lg(lo)) / (lg(hi) - lg(lo))) * HE;
  const x = (i: number) => ML + (i / (n - 1)) * iw;

  const ddLo = Math.min(...curve.drawdown, -0.01);
  const yD = (v: number) => MT + HE + GAP + (v / ddLo) * HD;

  const path = (vals: number[], yf: (v: number) => number) =>
    vals.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${yf(v).toFixed(1)}`).join(" ");

  const hIdx = curve.dates.findIndex((d) => d >= curve.holdout_start);
  const hx = hIdx > 0 ? x(hIdx) : null;

  const yTicks = [lo, Math.sqrt(lo * hi), hi];
  const xTicks = [0, Math.floor(n / 3), Math.floor((2 * n) / 3), n - 1];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img"
      aria-label="Cumulative wealth, naive versus honest, with drawdown">
      {hx !== null && (
        <>
          <rect x={hx} y={MT} width={W - MR - hx} height={HE + GAP + HD} fill="var(--shade)" />
          <line x1={hx} x2={hx} y1={MT} y2={MT + HE + GAP + HD} stroke="var(--rule-strong)" strokeDasharray="3 3" />
          <text x={hx + 6} y={MT + 12} style={{ fontSize: 10.5, fill: "var(--muted)" }}>
            holdout (never used for selection)
          </text>
        </>
      )}
      {yTicks.map((t, i) => (
        <g key={i}>
          <line x1={ML} x2={W - MR} y1={yE(t)} y2={yE(t)} className="axis" opacity={0.5} />
          <text x={ML - 7} y={yE(t) + 3.5} textAnchor="end" className="val">{t.toFixed(2)}×</text>
        </g>
      ))}
      <path d={path(curve.naive, yE)} fill="none" stroke="var(--d-blue)" strokeWidth={1.7} strokeDasharray="5 3" />
      <path d={path(curve.honest, yE)} fill="none" stroke="var(--d-green)" strokeWidth={1.9} />
      <text x={W - MR - 4} y={yE(curve.naive[n - 1]!) - 5} textAnchor="end"
        style={{ fill: "var(--d-blue)", fontSize: 11, fontWeight: 600 }}>naive</text>
      <text x={W - MR - 4} y={yE(curve.honest[n - 1]!) + 13} textAnchor="end"
        style={{ fill: "var(--d-green)", fontSize: 11, fontWeight: 600 }}>honest</text>
      <text x={ML - 44} y={MT + HE / 2} transform={`rotate(-90 ${ML - 44} ${MT + HE / 2})`}
        textAnchor="middle" style={{ fontSize: 11 }}>growth of 1 (log scale)</text>

      <path d={`${path(curve.drawdown, yD)} L${x(n - 1)} ${yD(0)} L${x(0)} ${yD(0)} Z`}
        fill="var(--d-vermillion)" opacity={0.22} />
      <path d={path(curve.drawdown, yD)} fill="none" stroke="var(--d-vermillion)" strokeWidth={1.2} />
      <line x1={ML} x2={W - MR} y1={yD(0)} y2={yD(0)} className="zero" />
      <text x={ML - 7} y={yD(ddLo) + 3.5} textAnchor="end" className="val">
        {(ddLo * 100).toFixed(0)}%
      </text>
      <text x={ML - 44} y={MT + HE + GAP + HD / 2}
        transform={`rotate(-90 ${ML - 44} ${MT + HE + GAP + HD / 2})`} textAnchor="middle"
        style={{ fontSize: 11 }}>drawdown</text>

      {xTicks.map((i) => (
        <text key={i} x={x(i)} y={H - 12} textAnchor="middle" className="val">
          {year(curve.dates[i]!)}
        </text>
      ))}
    </svg>
  );
}
