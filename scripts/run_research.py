"""Run the whole study and write results/ as JSON. Deterministic given the config."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from svtax import costs as C
from svtax import inference, pipeline, risk
from svtax import metrics as M
from svtax import stats as S
from svtax.backtest import BacktestConfig, BacktestResult
from svtax.config import DEFAULT, Config
from svtax.ladder import build_ladder, ladder_frame
from svtax.trials import TrialLog

CACHE = Path("data/raw")
OUT = Path("results")
SIGNALS = ("mom_12_1", "strev_1", "lowvol", "composite")
LABELS = {
    "mom_12_1": "12-1 Momentum",
    "strev_1": "1-Month Reversal",
    "lowvol": "Low Volatility",
    "composite": "Equal-Weight Composite",
}


def _j(obj: object) -> object:
    """JSON-safe conversion: NaN and numpy scalars become null / plain floats."""
    if isinstance(obj, dict):
        return {k: _j(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_j(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return None if not np.isfinite(f) else round(f, 6)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, np.ndarray):
        return [_j(v) for v in obj.tolist()]
    return obj


def main(cfg: Config = DEFAULT) -> None:
    """Run every section of the study in order and write results/ from one pass."""
    t0 = time.time()
    OUT.mkdir(exist_ok=True)
    rng = np.random.default_rng(cfg.seed)

    print("building study panels ...", flush=True)
    study = pipeline.build_study(CACHE, cfg)
    runner = pipeline.make_runner(study)
    log = TrialLog(cfg.hash(), cfg.seed)

    # ---- every pre-registered configuration, logged before anything is selected ----
    print("running pre-registered grid ...", flush=True)
    for sig in SIGNALS:
        for gc in pipeline.grid_for(sig):
            res = runner(gc)
            log.record(res, cfg.train_end, f"{sig}|{gc.scheme}|q{gc.n_quantiles}|f{gc.formation}")
    print(f"  {log.n_trials} configurations logged", flush=True)
    trial_sharpes = log.sharpes().to_numpy()

    results: dict[str, object] = {}

    # ---- the ladder, per signal ----
    print("building ladders ...", flush=True)
    ladders: dict[str, object] = {}
    honest_returns: dict[str, pd.Series] = {}
    for sig in SIGNALS:
        lad = build_ladder(
            signal=sig,
            runner=runner,
            grid=pipeline.grid_for(sig),
            train_end=cfg.train_end,
            trial_sharpes=trial_sharpes,
        )
        ladders[sig] = {
            "label": LABELS[sig],
            "rungs": ladder_frame(lad).to_dict("records"),
            "total_decay": lad.total_decay,
        }
        honest_returns[sig] = lad.honest_result.net
        print(
            f"  {sig:10s} L0={lad.rungs[0].sharpe:6.3f} -> L4={lad.rungs[-1].sharpe:6.3f}",
            flush=True,
        )
    results["ladders"] = ladders

    # ---- equity curves: naive vs honest, plus the benchmark ----
    print("equity curves ...", flush=True)
    curves: dict[str, object] = {}
    for sig in SIGNALS:
        lad_naive = runner(
            replace(
                pipeline.grid_for(sig)[0],
                naive_universe=True,
                same_close_execution=True,
                apply_costs=False,
            )
        )
        honest = honest_returns[sig]
        idx = honest.index
        curves[sig] = {
            "dates": [int(d.timestamp()) for d in idx],
            "naive": (1 + lad_naive.gross.reindex(idx).fillna(0)).cumprod().tolist(),
            "honest": (1 + honest.fillna(0)).cumprod().tolist(),
            "drawdown": (
                (1 + honest.fillna(0)).cumprod() / (1 + honest.fillna(0)).cumprod().cummax() - 1
            ).tolist(),
            "holdout_start": int(pd.Timestamp(cfg.train_end).timestamp()),
        }
    results["curves"] = curves

    # ---- cost decay and break-even ----
    print("cost curves ...", flush=True)
    cost_curves: dict[str, object] = {}
    for sig in SIGNALS:
        base = pipeline.grid_for(sig)[0]
        pts = []
        for bps in (0, 2, 5, 10, 15, 20, 25, 30, 40, 50):
            r = runner(replace(base, apply_costs=True, flat_cost_bps=float(bps)))
            pts.append({"bps": bps, "sharpe": M.sharpe(r.net)})
        gross = runner(replace(base, apply_costs=False))
        be = C.break_even_cost_bps(float(gross.gross.mean()), float(gross.turnover.mean()))
        cost_curves[sig] = {
            "label": LABELS[sig],
            "points": pts,
            "break_even_bps": be,
            "ann_turnover": gross.ann_turnover,
        }
    results["cost_curves"] = cost_curves

    # ---- decile monotonicity ----
    print("decile profiles ...", flush=True)
    deciles: dict[str, object] = {}
    for sig in SIGNALS:
        f = pipeline.SIGNAL_PARAMS[sig][-1]
        z = pipeline.standardized(study, sig, f, naive=False)
        prof = risk.decile_profile(z, study.mask_pit, study.panels.ret_next_open.reindex_like(z))
        deciles[sig] = {
            "label": LABELS[sig],
            "rows": prof.to_dict("records"),
            "spearman": risk.spearman_monotonicity(prof),
        }
    results["deciles"] = deciles

    # ---- factor attribution + risk ----
    print("attribution ...", flush=True)
    attribution: dict[str, object] = {}
    for sig in SIGNALS:
        a = risk.attribute(honest_returns[sig], study.factors, "FF5+UMD")
        attribution[sig] = {
            "label": LABELS[sig],
            **asdict(a),
            "metrics": M.summary(honest_returns[sig]),
            "crash": risk.crash_regression(honest_returns[sig], study.factors),
        }
    results["attribution"] = attribution

    # ---- multiple testing ----
    print("multiple-testing panel ...", flush=True)
    ret_mat = log.returns_matrix()
    pbo = S.cscv_pbo(ret_mat, n_blocks=cfg.cscv_blocks)
    primary = honest_returns["mom_12_1"]
    results["multiple_testing"] = {
        "n_trials": log.n_trials,
        "pbo": pbo.pbo,
        "is_oos_slope": pbo.slope,
        "prob_oos_loss": pbo.prob_oos_loss,
        "scatter": [
            {"is": a, "oos": b}
            for a, b in zip(pbo.is_sharpes[::7], pbo.oos_sharpes[::7], strict=False)
        ],
        "expected_max_sharpe_null": S.expected_max_sharpe(trial_sharpes),
        "trial_sharpes_is": log.frame()["sharpe_is"].tolist(),
        "trial_sharpes_oos": log.frame()["sharpe_oos"].tolist(),
        "min_detectable_sharpe": S.min_detectable_sharpe(len(primary)),
        "deflated_sharpe_prob": S.deflated_sharpe(primary, trial_sharpes),
        "haircut": S.haircut_sharpe(M.sharpe(primary), log.n_trials, len(primary)),
    }

    # ---- permutation test + bootstrap on the primary signal ----
    print("permutation test ...", flush=True)
    f = pipeline.SIGNAL_PARAMS["mom_12_1"][-1]
    z_primary = pipeline.standardized(study, "mom_12_1", f, naive=False)
    base_cfg = BacktestConfig(signal="mom_12_1", scheme="decile", formation=f)

    def _result(zz: pd.DataFrame) -> BacktestResult:
        from svtax.backtest import run as _run

        return _run(
            cfg=base_cfg,
            z=zz,
            mask=study.mask_pit,
            ret_same_close=study.panels.ret_same_close,
            ret_next_open=study.panels.ret_next_open,
            vol=study.vol,
            half_spread_bps=study.half_spread_bps,
            impact_bps=cfg.impact_bps,
            borrow_bps=cfg.borrow_bps_annual,
            start=cfg.sample_start,
            end=cfg.sample_end,
        )

    def run_with(zz: pd.DataFrame, *, net: bool) -> pd.Series:
        res = _result(zz)
        return res.net if net else res.gross

    # The permutation test runs on GROSS returns by necessity. Permuting the signal
    # destroys the month-to-month persistence of the weights, which roughly doubles
    # turnover; charging costs would then compare a low-turnover real signal against
    # high-turnover random ones, and the test would measure the cost model rather
    # than the signal. Costs are addressed separately, by the break-even analysis.
    placebo = pd.DataFrame(
        rng.standard_normal(z_primary.shape),
        index=z_primary.index,
        columns=z_primary.columns,
    )
    obs_gross = M.sharpe(runner(base_cfg).gross)
    perm = inference.permutation_test(
        z_primary, obs_gross, lambda zz: run_with(zz, net=False), cfg.n_permutations, rng
    )
    lo, hi = inference.stationary_bootstrap_ci(primary, M.sharpe, cfg.n_bootstrap, rng)
    results["inference"] = {"permutation": perm, "sharpe_ci95": [lo, hi]}

    # L3 -> L4 changes two things at once: the reporting discipline AND the sample
    # period. Isolate the period effect so the ladder's last step is interpretable.
    period_effect: dict[str, object] = {}
    for sig in SIGNALS:
        base = replace(pipeline.grid_for(sig)[0], apply_costs=True)
        full = runner(base).net
        period_effect[sig] = {
            "full_sample_sharpe": M.sharpe(full),
            "train_sharpe": M.sharpe(full.loc[: cfg.train_end]),
            "holdout_sharpe": M.sharpe(full.loc[cfg.train_end :].iloc[1:]),
        }
    results["period_effect"] = period_effect
    print(f"  permutation p={perm['p_value']:.4f}", flush=True)

    # ---- negative controls ----
    print("negative controls ...", flush=True)
    placebo_draws = [
        M.sharpe(
            run_with(
                pd.DataFrame(
                    rng.standard_normal(z_primary.shape),
                    index=z_primary.index,
                    columns=z_primary.columns,
                ),
                net=False,
            )
        )
        for _ in range(50)
    ]
    # Controls are reported gross, for the same reason as the permutation test.
    results["negative_controls"] = {
        # A single placebo draw is not a control: its sampling standard deviation is
        # the same ~0.26 as the permutation null, so any one draw lands anywhere in
        # that range. Report the distribution over many draws instead.
        "placebo_sharpe_gross": float(np.mean(placebo_draws)),
        "placebo_sharpe_sd": float(np.std(placebo_draws, ddof=1)),
        "placebo_n_draws": float(len(placebo_draws)),
        "stale_signal_sharpe_gross": M.sharpe(run_with(z_primary.shift(2), net=False)),
        "leaked_signal_sharpe_gross": M.sharpe(run_with(z_primary.shift(-1), net=False)),
        "honest_sharpe_gross": obs_gross,
        # Turnover of the real signal against permuted and placebo ones. Permuting
        # destroys the month-to-month persistence of the weights, so the permuted book
        # trades far more. This is precisely why the first version of the permutation
        # test, which charged costs to both arms, measured the cost model rather than
        # the signal: the charge landed almost entirely on the null.
        "real_turnover": float(_result(z_primary).ann_turnover),
        "placebo_turnover": float(_result(placebo).ann_turnover),
        "permuted_turnover_mean": float(
            np.mean(
                [
                    _result(inference.permute_within_date(z_primary, rng)).ann_turnover
                    for _ in range(25)
                ]
            )
        ),
        "note": (
            "The leakage probe is weak on real data because momentum is highly "
            "autocorrelated month to month, so next month's signal resembles this "
            "month's. The decisive leakage evidence is tests/test_no_lookahead.py, "
            "which plants a contemporaneous-only relationship the engine must fail "
            "to exploit."
        ),
    }

    # ---- parameter sensitivity ----
    print("sensitivity surface ...", flush=True)
    grid_cells = []
    for f_ in pipeline.SIGNAL_PARAMS["mom_12_1"]:
        for scheme in pipeline.SCHEMES:
            for q in pipeline.QUANTILES:
                r = runner(
                    BacktestConfig(signal="mom_12_1", scheme=scheme, n_quantiles=q, formation=f_)
                )
                oos = r.net.loc[cfg.train_end :].iloc[1:]
                grid_cells.append(
                    {"formation": f_, "scheme": scheme, "quantiles": q, "oos_sharpe": M.sharpe(oos)}
                )
    vals = np.array([c["oos_sharpe"] for c in grid_cells], dtype=float)
    finite = vals[np.isfinite(vals)]
    results["sensitivity"] = {
        "cells": grid_cells,
        "median": float(np.median(finite)),
        "max": float(finite.max()),
        "frac_positive": float((finite > 0).mean()),
        "max_over_median": float(finite.max() / np.median(finite)) if np.median(finite) else None,
    }

    # ---- survivorship coverage, the measurement that motivates everything ----
    cov = study.coverage[study.coverage.index >= cfg.sample_start]
    yearly = cov.resample("YE").mean()
    results["coverage"] = {
        "dates": [int(d.timestamp()) for d in yearly.index],
        "coverage": yearly["coverage"].tolist(),
        "n_true": yearly["n_true"].tolist(),
        "n_available": yearly["n_available"].tolist(),
        "mean_coverage": float(cov["coverage"].mean()),
        "mean_missing": float((cov["n_true"] - cov["n_available"]).mean()),
        "universe_pit": float(study.mask_pit.loc[cfg.sample_start :].sum(axis=1).mean()),
        "universe_naive": float(study.mask_naive.loc[cfg.sample_start :].sum(axis=1).mean()),
    }

    # ---- cost-model provenance: the estimator that did not work ----
    spread = C.corwin_schultz_spread(study.panels.high, study.panels.low).loc[cfg.sample_start :]
    results["cost_model"] = {
        "primary_bps_per_side": cfg.primary_cost_bps,
        "borrow_bps_annual": cfg.borrow_bps_annual,
        "corwin_schultz": C.cs_diagnostics(spread),
    }

    results["meta"] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "git_sha": log.sha,
        "config_hash": cfg.hash(),
        "seed": cfg.seed,
        "sample": [cfg.sample_start, cfg.sample_end],
        "train_end": cfg.train_end,
        "n_months": len(primary),
        "runtime_s": round(time.time() - t0, 1),
    }

    log.write(OUT)
    (OUT / "results.json").write_text(json.dumps(_j(results), indent=1))
    print(f"\nwrote results/results.json in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
