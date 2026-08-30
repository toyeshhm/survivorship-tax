/** Fixed precision per column: mixed precision in one column reads as carelessness. */
export const f2 = (v: number | null | undefined): string =>
  v === null || v === undefined || !Number.isFinite(v) ? "—" : v.toFixed(2);
export const f3 = (v: number | null | undefined): string =>
  v === null || v === undefined || !Number.isFinite(v) ? "—" : v.toFixed(3);
export const pct1 = (v: number | null | undefined): string =>
  v === null || v === undefined || !Number.isFinite(v) ? "—" : `${(v * 100).toFixed(1)}%`;
export const bps0 = (v: number | null | undefined): string =>
  v === null || v === undefined || !Number.isFinite(v) ? "—" : `${Math.round(v)}`;
/** Always print the sign: colour must never be the only encoding of direction. */
export const signed = (v: number | null | undefined, dp = 3): string =>
  v === null || v === undefined || !Number.isFinite(v)
    ? "—"
    : `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(dp)}`;
export const year = (epoch: number): string =>
  new Date(epoch * 1000).getUTCFullYear().toString();
