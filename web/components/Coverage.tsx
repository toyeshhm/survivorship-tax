import { year } from "@/lib/fmt";

/**
 * The measurement the whole study rests on: what fraction of the true index the
 * free data source can actually price, by year. The gap is the companies that left
 * the index and were erased with it.
 */
export function Coverage({
  dates, coverage,
}: { dates: number[]; coverage: number[] }) {
  const W = 720, H = 210, ML = 46, MR = 16, MT = 16, MB = 34;
  const iw = W - ML - MR, ih = H - MT - MB;
  const n = dates.length;
  const x = (i: number) => ML + (i / (n - 1)) * iw;
  const y = (v: number) => MT + ih - ((v - 0.6) / (1 - 0.6)) * ih;
  const d = coverage.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img"
      aria-label="Share of true index members priceable from free data, by year">
      {[0.6, 0.7, 0.8, 0.9, 1].map((t) => (
        <g key={t}>
          <line x1={ML} x2={W - MR} y1={y(t)} y2={y(t)} className="axis" opacity={0.5} />
          <text x={ML - 7} y={y(t) + 3.5} textAnchor="end" className="val">
            {(t * 100).toFixed(0)}%
          </text>
        </g>
      ))}
      <path d={`${d} L${x(n - 1)} ${y(0.6)} L${x(0)} ${y(0.6)} Z`} fill="var(--d-vermillion)" opacity={0.1} />
      <path d={d} fill="none" stroke="var(--d-vermillion)" strokeWidth={2} />
      {coverage.map((v, i) => <circle key={i} cx={x(i)} cy={y(v)} r={2.2} fill="var(--d-vermillion)" />)}
      {dates.map((dt, i) =>
        i % 2 === 0 ? (
          <text key={i} x={x(i)} y={H - 12} textAnchor="middle" className="val">{year(dt)}</text>
        ) : null,
      )}
      <text x={ML - 34} y={MT + ih / 2} transform={`rotate(-90 ${ML - 34} ${MT + ih / 2})`}
        textAnchor="middle" style={{ fontSize: 11 }}>index priceable</text>
    </svg>
  );
}
