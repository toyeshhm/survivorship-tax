export type Rung = {
  rung: string; label: string; sharpe: number; delta: number;
  n_periods: number; note: string;
};
export type Ladder = { label: string; rungs: Rung[]; total_decay: number };
export type Curve = {
  dates: number[]; naive: number[]; honest: number[];
  drawdown: number[]; holdout_start: number;
};
export type CostCurve = {
  label: string; points: { bps: number; sharpe: number | null }[];
  break_even_bps: number | null; ann_turnover: number;
};
export type DecileRow = {
  decile: number; mean_monthly: number; ann_return: number;
  excess_ann: number; n_obs: number;
};
export type Decile = { label: string; rows: DecileRow[]; spearman: number | null };
export type Attribution = {
  label: string; alpha_annual: number | null; alpha_t: number | null;
  betas: Record<string, number | null>; tstats: Record<string, number | null>;
  r_squared: number | null; info_ratio: number | null; n_obs: number; lags: number;
  metrics: Record<string, number | null>;
  crash: Record<string, number | null>;
};
export type Results = {
  ladders: Record<string, Ladder>;
  curves: Record<string, Curve>;
  cost_curves: Record<string, CostCurve>;
  deciles: Record<string, Decile>;
  attribution: Record<string, Attribution>;
  multiple_testing: {
    n_trials: number; pbo: number | null; is_oos_slope: number | null;
    prob_oos_loss: number | null; scatter: { is: number; oos: number }[];
    expected_max_sharpe_null: number | null;
    trial_sharpes_is: (number | null)[]; trial_sharpes_oos: (number | null)[];
    min_detectable_sharpe: number | null; deflated_sharpe_prob: number | null;
    haircut: Record<string, number | null>;
  };
  inference: {
    permutation: Record<string, number | null>;
    sharpe_ci95: (number | null)[];
  };
  negative_controls: Record<string, number | string | null>;
  period_effect: Record<string, Record<string, number | null>>;
  sensitivity: {
    cells: { formation: number; scheme: string; quantiles: number; oos_sharpe: number | null }[];
    median: number | null; max: number | null; frac_positive: number | null;
    max_over_median: number | null;
  };
  coverage: {
    dates: number[]; coverage: number[]; n_true: number[]; n_available: number[];
    mean_coverage: number; mean_missing: number;
    universe_pit: number; universe_naive: number;
  };
  cost_model: {
    primary_bps_per_side: number; borrow_bps_annual: number;
    corwin_schultz: Record<string, number | null>;
  };
  meta: {
    generated_at: string; git_sha: string; config_hash: string; seed: number;
    sample: string[]; train_end: string; n_months: number; runtime_s: number;
  };
};
