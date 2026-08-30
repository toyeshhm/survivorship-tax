"""End-to-end pipeline smoke test on synthetic panels, for CI.

Unit tests can pass while the study itself is broken. This runs the real engine,
ladder, and statistics over generated data and asserts the shapes and invariants
that every downstream artifact depends on.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from svtax import metrics as M
from svtax import stats as S
from svtax.backtest import BacktestConfig, BacktestResult, run
from svtax.ladder import RUNGS, build_ladder

N_MONTHS, N_NAMES = 150, 60


def synthetic() -> tuple[pd.DataFrame, ...]:
    """Panels with a planted t-1 signal, long enough that the ladder's holdout is real."""
    rng = np.random.default_rng(0)
    idx = pd.date_range("2012-01-31", periods=N_MONTHS, freq="ME")
    cols = [f"T{i:03d}" for i in range(N_NAMES)]
    z = pd.DataFrame(rng.standard_normal((N_MONTHS, N_NAMES)), index=idx, columns=cols)
    z = z.sub(z.mean(axis=1), axis=0).div(z.std(axis=1, ddof=0), axis=0)
    ret = pd.DataFrame(rng.standard_normal((N_MONTHS, N_NAMES)) * 0.06, index=idx, columns=cols)
    ret += 0.015 * z.shift(1).fillna(0.0)
    mask = pd.DataFrame(data=True, index=idx, columns=cols)
    vol = pd.DataFrame(0.02, index=idx, columns=cols)
    spread = pd.DataFrame(5.0, index=idx, columns=cols)
    return z, mask, ret, vol, spread


def main() -> int:
    """Run the engine, ladder, and statistics end to end and assert their invariants."""
    z, mask, ret, vol, spread = synthetic()
    start, end = str(z.index[0].date()), str(z.index[-1].date())

    def runner(cfg: BacktestConfig) -> BacktestResult:
        return run(
            cfg=cfg,
            z=z,
            mask=mask,
            ret_same_close=ret,
            ret_next_open=ret,
            vol=vol,
            half_spread_bps=spread,
            impact_bps=1.0,
            borrow_bps=40.0,
            start=start,
            end=end,
        )

    grid = [
        BacktestConfig(signal="synthetic", scheme=s, n_quantiles=q)
        for s in ("decile", "rank", "invvol")
        for q in (5, 10)
    ]
    trial_sharpes = np.array([M.sharpe(runner(g).net) for g in grid])

    lad = build_ladder(
        signal="synthetic",
        runner=runner,
        grid=grid,
        train_end="2019-12-31",
        trial_sharpes=trial_sharpes,
    )
    assert len(lad.rungs) == len(RUNGS), "the ladder must report every rung"
    assert all(np.isfinite(r.sharpe) for r in lad.rungs), "every rung needs a finite Sharpe"

    base = runner(grid[0])
    assert len(base.net) == len(base.gross) == len(base.turnover)
    assert (base.turnover >= 0).all(), "turnover cannot be negative"
    assert (base.cost >= 0).all(), "costs cannot be negative"
    assert (base.net <= base.gross + 1e-12).all(), "net can never exceed gross"

    mat = pd.DataFrame({f"c{i}": runner(g).net for i, g in enumerate(grid)})
    pbo = S.cscv_pbo(mat, n_blocks=10)
    assert 0.0 <= pbo.pbo <= 1.0, "PBO must be a probability"
    assert np.isfinite(S.deflated_sharpe(base.net, trial_sharpes))

    print(f"smoke OK: L0={lad.rungs[0].sharpe:.3f} L4={lad.rungs[-1].sharpe:.3f} PBO={pbo.pbo:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
