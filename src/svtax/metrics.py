"""Performance and risk metrics. Every definition here is pinned by a unit test."""

from __future__ import annotations

from dataclasses import dataclass
from typing import SupportsFloat, cast

import numpy as np
import pandas as pd

MONTHS = 12
DAYS = 252

# A standard deviation needs two observations before it means anything, so the
# dispersion-based metrics return NaN rather than a number below this length.
MIN_OBS_FOR_SD = 2


def _ann(periods_per_year: int) -> float:
    return float(np.sqrt(periods_per_year))


def sharpe(returns: pd.Series, ppy: int = MONTHS) -> float:
    """Annualized Sharpe ratio of an excess-return series (population sd, ddof=0)."""
    r = returns.dropna()
    if len(r) < MIN_OBS_FOR_SD:
        return float("nan")
    sd = float(r.std(ddof=0))
    return float("nan") if sd == 0 else float(r.mean() / sd * _ann(ppy))


def sortino(returns: pd.Series, ppy: int = MONTHS) -> float:
    """Annualized Sortino. Downside deviation uses the FULL n in the denominator.

    Dividing only by the count of negative periods is the common bug: it makes a
    strategy with few, large losses look better than one with many small ones.
    """
    r = returns.dropna()
    if len(r) < MIN_OBS_FOR_SD:
        return float("nan")
    downside = np.minimum(r.to_numpy(), 0.0)
    dd = float(np.sqrt(np.mean(downside**2)))
    return float("nan") if dd == 0 else float(r.mean() / dd * _ann(ppy))


def cagr(returns: pd.Series, ppy: int = MONTHS) -> float:
    """Compound annual growth rate of the wealth path. NaN if the path ends non-positive."""
    r = returns.dropna()
    if r.empty:
        return float("nan")
    total = float(cast("SupportsFloat", (1.0 + r).prod()))
    years = len(r) / ppy
    if years <= 0 or total <= 0:
        return float("nan")
    return float(total ** (1.0 / years) - 1.0)


def ann_vol(returns: pd.Series, ppy: int = MONTHS) -> float:
    """Annualized volatility, on the same population sd convention as `sharpe`."""
    return float(returns.dropna().std(ddof=0) * _ann(ppy))


@dataclass(frozen=True, slots=True)
class Drawdown:
    """Max drawdown paired with its duration - the pair is the honest report."""

    max_dd: float
    peak_date: pd.Timestamp | None
    trough_date: pd.Timestamp | None
    recovery_date: pd.Timestamp | None
    duration_periods: int
    time_under_water: int


def drawdown(returns: pd.Series) -> Drawdown:
    """Max drawdown of the compounded wealth path, with duration and time under water."""
    r = returns.dropna()
    if r.empty:
        return Drawdown(float("nan"), None, None, None, 0, 0)
    wealth = (1.0 + r).cumprod()
    peak = wealth.cummax()
    dd = wealth / peak - 1.0
    # `idxmin`/`idxmax` are typed as the generic label union; every caller here
    # passes a date-indexed return series, which is what `Drawdown` records.
    trough = cast("pd.Timestamp", dd.idxmin())
    max_dd = float(dd.min())
    prior = wealth.loc[:trough]
    peak_date = cast("pd.Timestamp", prior.idxmax())
    after = wealth.loc[trough:]
    peak_level = float(wealth.loc[peak_date])
    recovered = after[after >= peak_level]
    recovery = recovered.index[0] if len(recovered) else None
    idx = list(r.index)
    dur = idx.index(trough) - idx.index(peak_date)
    tuw = int((dd < 0).sum())
    return Drawdown(max_dd, peak_date, trough, recovery, int(dur), tuw)


def var_cvar(returns: pd.Series, alpha: float = 0.05) -> tuple[float, float]:
    """Historical VaR and CVaR (expected shortfall) at the given tail probability."""
    r = returns.dropna()
    if len(r) < MIN_OBS_FOR_SD:
        return float("nan"), float("nan")
    cut = float(np.quantile(r.to_numpy(), alpha))
    tail = r[r <= cut]
    return cut, float(tail.mean()) if len(tail) else float("nan")


def summary(returns: pd.Series, ppy: int = MONTHS) -> dict[str, float]:
    """The metric block reported for every sleeve."""
    r = returns.dropna()
    dd = drawdown(r)
    var, cvar = var_cvar(r)
    return {
        "n_periods": float(len(r)),
        "cagr": cagr(r, ppy),
        "ann_vol": ann_vol(r, ppy),
        "sharpe": sharpe(r, ppy),
        "sortino": sortino(r, ppy),
        "skew": float(cast("SupportsFloat", r.skew())),
        "excess_kurtosis": float(cast("SupportsFloat", r.kurtosis())),
        "worst_period": float(r.min()) if len(r) else float("nan"),
        "max_drawdown": dd.max_dd,
        "dd_duration": float(dd.duration_periods),
        "time_under_water": float(dd.time_under_water),
        "var_5": var,
        "cvar_5": cvar,
        "hit_rate": float((r > 0).mean()) if len(r) else float("nan"),
    }
