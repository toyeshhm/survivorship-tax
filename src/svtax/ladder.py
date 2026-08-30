"""The bias ladder: the project's headline object.

Five nested configurations take the same signal from a naive student-grade backtest
to a defensible one, one shortcut removed per rung. The drop in Sharpe at each rung
is that shortcut's contribution to the inflation - the survivorship tax, itemized.

  L0 Naive      backfilled current constituents, same-close fill, zero costs,
                best of the parameter grid reported over the full sample
  L1 +PIT       point-in-time index membership
  L2 +T+1       fill at the next open, forfeiting the overnight gap
  L3 +costs     per-name Corwin-Schultz spread, impact, and short borrow
  L4 +honest    holdout only, at the parameter picked on training data,
                Sharpe deflated for the number of trials run
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from svtax import metrics as M
from svtax import stats as S
from svtax.backtest import BacktestConfig, BacktestResult

RUNGS: tuple[tuple[str, str], ...] = (
    ("L0", "Naive"),
    ("L1", "+ Point-in-time universe"),
    ("L2", "+ T+1 execution"),
    ("L3", "+ Transaction costs"),
    ("L4", "+ Honest reporting"),
)


@dataclass(frozen=True, slots=True)
class Rung:
    """One step of the ladder."""

    key: str
    label: str
    sharpe: float
    delta: float
    config: BacktestConfig
    n_periods: int
    note: str = ""


@dataclass(frozen=True, slots=True)
class LadderResult:
    """One signal's five rungs, plus the runs sitting at either end of them.

    `naive_result` is the best naive grid cell over the full sample - the number a
    student-grade backtest would report. `honest_result` is the configuration chosen
    on training data alone, whose holdout stretch is what L4 reports.
    """

    signal: str
    rungs: list[Rung]
    naive_result: BacktestResult
    honest_result: BacktestResult

    @property
    def total_decay(self) -> float:
        """Sharpe lost between the naive rung and the honest one: the tax itself."""
        return self.rungs[0].sharpe - self.rungs[-1].sharpe


def _sharpe(r: BacktestResult, *, net: bool) -> float:
    return M.sharpe(r.net if net else r.gross)


def build_ladder(
    *,
    signal: str,
    runner: Callable[[BacktestConfig], BacktestResult],
    grid: list[BacktestConfig],
    train_end: str,
    trial_sharpes: np.ndarray,
) -> LadderResult:
    """Walk the five rungs for one signal.

    `runner` maps a BacktestConfig to a BacktestResult over the full sample; it
    closes over the panels so this module stays free of data plumbing.
    """
    # L0: the naive setup, reported at its best grid cell over the full sample.
    naive_grid = [
        replace(c, naive_universe=True, same_close_execution=True, apply_costs=False) for c in grid
    ]
    naive_runs = [(c, runner(c)) for c in naive_grid]
    best_cfg, best_run = max(naive_runs, key=lambda kv: _sharpe(kv[1], net=False))
    l0 = _sharpe(best_run, net=False)

    # L1..L3 keep the winning parameters and remove one shortcut at a time.
    base = replace(best_cfg, naive_universe=False)
    r1 = runner(replace(base, same_close_execution=True, apply_costs=False))
    l1 = _sharpe(r1, net=False)
    r2 = runner(replace(base, same_close_execution=False, apply_costs=False))
    l2 = _sharpe(r2, net=False)
    r3 = runner(replace(base, same_close_execution=False, apply_costs=True))
    l3 = _sharpe(r3, net=True)

    # L4: choose parameters on training data only, then report the untouched holdout.
    honest_grid = [
        replace(c, naive_universe=False, same_close_execution=False, apply_costs=True) for c in grid
    ]
    scored = []
    for c in honest_grid:
        res = runner(c)
        scored.append((c, res, M.sharpe(res.net.loc[:train_end])))
    picked_cfg, picked_res, _ = max(scored, key=lambda t: t[2])
    holdout = picked_res.net.loc[train_end:]
    holdout = holdout.iloc[1:] if len(holdout) else holdout
    l4_raw = M.sharpe(holdout)

    # Deflate the holdout Sharpe for the number of configurations searched.
    dsr = (
        S.deflated_sharpe(holdout, trial_sharpes)
        if len(holdout) > S.MIN_OBS_MOMENTS
        else float("nan")
    )
    l4 = l4_raw

    rungs = [
        Rung("L0", "Naive", l0, 0.0, best_cfg, len(best_run.gross)),
        Rung("L1", "+ Point-in-time universe", l1, l1 - l0, base, len(r1.gross)),
        Rung("L2", "+ T+1 execution", l2, l2 - l1, base, len(r2.gross)),
        Rung("L3", "+ Transaction costs", l3, l3 - l2, base, len(r3.gross)),
        Rung(
            "L4",
            "+ Honest reporting",
            l4,
            l4 - l3,
            picked_cfg,
            len(holdout),
            note=f"holdout only; deflated Sharpe probability {dsr:.3f}",
        ),
    ]
    return LadderResult(signal, rungs, best_run, picked_res)


def ladder_frame(res: LadderResult) -> pd.DataFrame:
    """Flatten a ladder into one row per rung, for reporting and serialization."""
    return pd.DataFrame(
        [
            {
                "rung": r.key,
                "label": r.label,
                "sharpe": r.sharpe,
                "delta": r.delta,
                "n_periods": r.n_periods,
                "note": r.note,
            }
            for r in res.rungs
        ]
    )
