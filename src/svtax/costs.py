"""Transaction costs from a per-name spread estimate, not a flat guess.

The Corwin-Schultz (2012) high-low estimator recovers an effective bid-ask spread
from daily high and low prices alone. Two-day highs and lows span more of the true
price range than two consecutive one-day ranges do; the gap between them identifies
the spread, because the spread inflates a single day's range less than two days'.
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd

_ALPHA_DEN = 3.0 - 2.0 * np.sqrt(2.0)


def corwin_schultz_spread(high: pd.DataFrame, low: pd.DataFrame, window: int = 21) -> pd.DataFrame:
    """Rolling mean of the daily Corwin-Schultz proportional spread estimate.

    Negative daily estimates are averaged in, and only the resulting MONTHLY mean is
    floored at zero. This ordering matters enormously: roughly 40% of daily estimates
    come out negative as pure sampling noise, so clipping each one to zero first
    discards the entire lower half of a mean-zero error distribution and inflates the
    estimate by more than an order of magnitude for liquid names.
    """
    hi, lo = high.astype(float), low.astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        # numpy ufuncs hand the DataFrame back at runtime, but their stubs only
        # describe the ndarray path - hence the casts where pandas methods follow.
        log_range = cast("pd.DataFrame", np.log(hi / lo) ** 2)
        beta = log_range + log_range.shift(1)
        h2 = hi.rolling(2).max()
        l2 = lo.rolling(2).min()
        gamma = np.log(h2 / l2) ** 2
        alpha = (np.sqrt(2.0 * beta) - np.sqrt(beta)) / _ALPHA_DEN - np.sqrt(gamma / _ALPHA_DEN)
        spread = cast("pd.DataFrame", 2.0 * (np.exp(alpha) - 1.0) / (1.0 + np.exp(alpha)))
    spread = spread.where(np.isfinite(spread))
    rolled = spread.rolling(window, min_periods=max(window // 3, 5)).mean()
    return rolled.clip(lower=0.0)


def monthly_half_spread_bps(
    high: pd.DataFrame,
    low: pd.DataFrame,
    month_ends: pd.DatetimeIndex,
    *,
    floor_bps: float = 1.0,
    cap_bps: float = 100.0,
) -> pd.DataFrame:
    """Per-name effective HALF-spread in basis points, sampled at each month end."""
    spread = corwin_schultz_spread(high, low)
    half_bps = spread.resample("ME").last().reindex(month_ends) * 0.5 * 10_000.0
    return half_bps.clip(lower=floor_bps, upper=cap_bps)


def trade_cost(
    weight_delta: pd.DataFrame, half_spread_bps: pd.DataFrame, impact_bps: float
) -> pd.Series:
    """Cost per rebalance: sum over names of |dw| times (half-spread + impact)."""
    per_name = (half_spread_bps + impact_bps) / 10_000.0
    aligned = per_name.reindex(index=weight_delta.index, columns=weight_delta.columns)
    # A name with no spread estimate is charged the cross-sectional median, never zero.
    filled = aligned.T.fillna(aligned.median(axis=1)).T
    return (weight_delta.abs() * filled).sum(axis=1)


def borrow_cost(short_gross: pd.Series, annual_bps: float) -> pd.Series:
    """Monthly stock-borrow accrual charged on the gross short leg."""
    return short_gross.abs() * (annual_bps / 10_000.0) / 12.0


def break_even_cost_bps(gross_mean_monthly: float, turnover_one_way_monthly: float) -> float:
    """Round-trip cost in bps that would exactly erase the gross edge."""
    if turnover_one_way_monthly <= 0:
        return float("inf")
    return float(gross_mean_monthly / (2.0 * turnover_one_way_monthly) * 10_000.0)


def cs_diagnostics(spread: pd.DataFrame) -> dict[str, float]:
    """Evidence on whether Corwin-Schultz can price this universe at all.

    For S&P 500 large caps the true effective spread sits below what daily high-low
    data can resolve, so most name-months return a non-positive estimate. Reported
    rather than hidden: it is why the headline cost model here is a swept flat cost
    with a break-even figure, not a per-name spread estimate.
    """
    stacked = spread.resample("ME").last().melt()["value"].dropna()
    positive = stacked[stacked > 0]
    return {
        "name_months": float(len(stacked)),
        "frac_non_positive": float((stacked <= 0).mean()),
        "median_positive_bps": float(positive.median() * 10_000.0)
        if len(positive)
        else float("nan"),
        "p90_positive_bps": float(positive.quantile(0.9) * 10_000.0)
        if len(positive)
        else float("nan"),
    }
