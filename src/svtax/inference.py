"""Permutation and bootstrap inference over the full construction pipeline."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from svtax import metrics as M

# One year of monthly returns. Below that the stationary bootstrap has nothing to
# resample: the expected block length approaches the length of the sample itself.
MIN_BOOTSTRAP_OBS = 12


def permute_within_date(z: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Shuffle the signal across names within each date, preserving everything else.

    Permuting the SIGNAL rather than the returns is the right null: it destroys the
    signal-return link while leaving the market factor and the cross-sectional
    correlation structure of returns intact. Permuting returns instead would break
    those too and make the null far too easy to beat.
    """
    out = z.to_numpy(copy=True)
    for i in range(out.shape[0]):
        row = out[i]
        finite = np.flatnonzero(np.isfinite(row))
        if finite.size > 1:
            row[finite] = rng.permutation(row[finite])
    return pd.DataFrame(out, index=z.index, columns=z.columns)


def permutation_test(
    z: pd.DataFrame,
    observed_sharpe: float,
    run_fn: Callable[[pd.DataFrame], pd.Series],
    n: int,
    rng: np.random.Generator,
) -> dict[str, float]:
    """p-value for the observed Sharpe against the within-date permutation null."""
    draws = np.empty(n, dtype=float)
    for i in range(n):
        draws[i] = M.sharpe(run_fn(permute_within_date(z, rng)))
    finite = draws[np.isfinite(draws)]
    ge = int((finite >= observed_sharpe).sum())
    return {
        "observed": float(observed_sharpe),
        "p_value": float((1 + ge) / (len(finite) + 1)),
        "null_mean": float(finite.mean()),
        "null_sd": float(finite.std(ddof=1)),
        "null_q95": float(np.quantile(finite, 0.95)),
        "n_draws": float(len(finite)),
    }


def stationary_bootstrap_ci(
    returns: pd.Series,
    stat: Callable[[pd.Series], float],
    n: int,
    rng: np.random.Generator,
    block: float | None = None,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Percentile CI under a stationary bootstrap with geometric block lengths.

    Blocks preserve the autocorrelation an i.i.d. bootstrap would destroy; the
    expected block length follows the usual n^(1/3) rule when not supplied.
    """
    r = returns.dropna()
    t = len(r)
    if t < MIN_BOOTSTRAP_OBS:
        return float("nan"), float("nan")
    expected_block = block if block is not None else max(t ** (1.0 / 3.0), 2.0)
    p = 1.0 / expected_block
    vals = np.empty(n, dtype=float)
    arr = r.to_numpy()
    for i in range(n):
        idx = np.empty(t, dtype=int)
        j = rng.integers(0, t)
        for k in range(t):
            idx[k] = j
            j = rng.integers(0, t) if rng.random() < p else (j + 1) % t
        vals[i] = stat(pd.Series(arr[idx]))
    finite = vals[np.isfinite(vals)]
    return float(np.quantile(finite, alpha / 2)), float(np.quantile(finite, 1 - alpha / 2))
