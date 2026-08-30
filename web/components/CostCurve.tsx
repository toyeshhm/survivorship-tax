import type { CostCurve as CC } from "@/lib/types";
import { bps0 } from "@/lib/fmt";

const COLORS = ["var(--d-green)", "var(--d-vermillion)", "var(--d-orange)", "var(--d-blue)"];
const DASH = ["", "5 3", "2 3", "8 3"];

/**
 * Net Sharpe as a function of assumed cost. Where a line crosses zero is the
 * signal's break-even cost, which is the one cost statistic that requires no
 * assumption about what trading actually costs.
 */
export function CostCurves({ series }: { series: [string, CC][] }) {
  const W = 760, H = 300, ML = 52, MR = 150, MT = 18, MB = 46;
  const iw = W - ML - MR, ih = H - MT - MB;
  const xs = series[0]![1].points.map((p) => p.bps);
  const xMax = Math.max(...xs);
  const vals = series.flatMap(([, s]) => s.points.map((p) => p.sharpe ?? 0));
  const hi = Math.max(...vals, 0.1), lo = Math.min(...vals, -0.1);
  const x = (b: number) => ML + (b / xMax) * iw;
  const y = (v: number) => MT + ih - ((v - lo) / (hi - lo)) * ih;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img"
      aria-label="Net Sharpe against assumed transaction cost per side">
      {[hi, (hi + lo) / 2, lo].map((t, i) => (
        <g key={i}>
          <line x1={ML} x2={W - MR} y1={y(t)} y2={y(t)} className="axis" opacity={0.5} />
          <text x={ML - 7} y={y(t) + 3.5} textAnchor="end" className="val">{t.toFixed(2)}</text>
        </g>
      ))}
      <line x1={ML} x2={W - MR} y1={y(0)} y2={y(0)} className="zero" />
      <rect x={x(5)} y={MT} width={x(15) - x(5)} height={ih} fill="var(--shade)" />
      <text x={x(10)} y={MT + 11} textAnchor="middle" style={{ fontSize: 10, fill: "var(--muted)" }}>
        plausible large-cap range
      </text>

      {series.map(([key, s], si) => {
        const d = s.points
          .map((p, i) => `${i ? "L" : "M"}${x(p.bps).toFixed(1)} ${y(p.sharpe ?? 0).toFixed(1)}`)
          .join(" ");
        const last = s.points[s.points.length - 1]!;
        return (
          <g key={key}>
            <path d={d} fill="none" stroke={COLORS[si % 4]} strokeWidth={1.8}
              strokeDasharray={DASH[si % 4]} />
            <text x={W - MR + 6} y={y(last.sharpe ?? 0) + 3.5}
              style={{ fill: COLORS[si % 4], fontSize: 10.5, fontWeight: 600 }}>
              {s.label.replace("Equal-Weight ", "")}
            </text>
            {s.break_even_bps !== null && s.break_even_bps > 0 && s.break_even_bps <= xMax && (
              <g>
                <circle cx={x(s.break_even_bps)} cy={y(0)} r={3.4} fill={COLORS[si % 4]} />
                <text x={x(s.break_even_bps)} y={y(0) + 16} textAnchor="middle" className="val"
                  style={{ fill: COLORS[si % 4], fontSize: 10 }}>
                  {bps0(s.break_even_bps)}
                </text>
              </g>
            )}
          </g>
        );
      })}
      {[0, 10, 20, 30, 40, 50].map((b) => (
        <text key={b} x={x(b)} y={H - 16} textAnchor="middle" className="val">{b}</text>
      ))}
      <text x={ML + iw / 2} y={H - 2} textAnchor="middle" style={{ fontSize: 11 }}>
        assumed cost per side (bps)
      </text>
    </svg>
  );
}
