import type { Decile } from "@/lib/types";
import { f2 } from "@/lib/fmt";

/**
 * Mean annualized forward return by signal decile, net of the cross-sectional mean.
 * Demeaning matters: raw decile returns are positive in every decile during a rising
 * market, so an undemeaned chart shows the market rather than the signal. A clean
 * spread climbs monotonically; the Spearman rho summarizes whether it does, and a
 * spread carried entirely by the bottom decile is a distress story, not a factor.
 */
export function DecileBars({ decile }: { decile: Decile }) {
  const W = 340, H = 200, ML = 34, MR = 8, MT = 14, MB = 30;
  const iw = W - ML - MR, ih = H - MT - MB;
  const vals = decile.rows.map((r) => r.excess_ann);
  const hi = Math.max(...vals, 0.01), lo = Math.min(...vals, -0.01);
  const y = (v: number) => MT + ih - ((v - lo) / (hi - lo)) * ih;
  const bw = (iw / decile.rows.length) * 0.7;

  return (
    <figure style={{ margin: 0 }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img"
        aria-label={`${decile.label}: mean annualized return by decile`}>
        <line x1={ML} x2={W - MR} y1={y(0)} y2={y(0)} className="zero" />
        {decile.rows.map((r, i) => {
          const cx = ML + (iw / decile.rows.length) * (i + 0.5);
          const top = Math.min(y(r.excess_ann), y(0));
          const h = Math.abs(y(r.excess_ann) - y(0));
          return (
            <rect key={r.decile} x={cx - bw / 2} y={top} width={bw} height={Math.max(h, 1)}
              rx={1} fill={r.excess_ann >= 0 ? "var(--d-green)" : "var(--d-vermillion)"} opacity={0.85} />
          );
        })}
        {[lo, hi].map((t, i) => (
          <text key={i} x={ML - 5} y={y(t) + 3.5} textAnchor="end" className="val"
            style={{ fontSize: 9.5 }}>{(t * 100).toFixed(0)}%</text>
        ))}
        <text x={ML} y={H - 10} className="val" style={{ fontSize: 10 }}>D1</text>
        <text x={W - MR} y={H - 10} textAnchor="end" className="val" style={{ fontSize: 10 }}>D10</text>
      </svg>
      <figcaption className="caption" style={{ marginTop: "0.3rem" }}>
        <strong style={{ color: "var(--ink-2)" }}>{decile.label}</strong>
        {" · Spearman ρ = "}
        <span className="val" style={{ color: "var(--ink)" }}>{f2(decile.spearman)}</span>
      </figcaption>
    </figure>
  );
}
