"""Cross-sectional signals. Each carries its economic mechanism in the docstring.

All three are price-based. Fundamental signals (book-to-market, gross profitability)
would need point-in-time SEC filings and are out of scope here - see docs/limitations.

Cross-sectional standardization (rank then z-score, per date) uses only information
available on that date. There is no time-series normalization anywhere in this file:
a full-sample mean or standard deviation would leak the future into the signal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _month_end(daily: pd.DataFrame) -> pd.DataFrame:
    return daily.resample("ME").last()


def mom_12_1(close: pd.DataFrame, formation: int = 12, skip: int = 1) -> pd.DataFrame:
    """Jegadeesh-Titman / Carhart momentum: return from t-12 to t-2, skipping t-1.

    Mechanism: under-reaction to news plus delayed diffusion of information. The
    skipped month purges short-horizon reversal and bid-ask bounce, which otherwise
    contaminate the signal with microstructure noise rather than the risk premium.
    """
    me = _month_end(close)
    return me.shift(skip) / me.shift(formation) - 1.0


def strev_1(close: pd.DataFrame) -> pd.DataFrame:
    """Short-term reversal: the negative of last month's return.

    Mechanism: liquidity provision. Buying last month's losers is compensation for
    absorbing selling pressure. Highest-turnover signal here, so it is the one the
    cost model is most likely to kill - which is precisely the hypothesis.
    """
    me = _month_end(close)
    return -(me / me.shift(1) - 1.0)


def lowvol(daily_ret: pd.DataFrame, window: int = 252, min_obs: int = 120) -> pd.DataFrame:
    """Low-volatility: negative trailing realized volatility of daily returns.

    Mechanism: leverage-constrained investors bid up high-beta names, leaving low-vol
    names cheap on a risk-adjusted basis (Frazzini-Pedersen betting-against-beta).
    """
    vol = daily_ret.rolling(window, min_periods=min_obs).std()
    return -_month_end(vol)


SIGNALS: dict[str, str] = {
    "mom_12_1": "12-1 momentum",
    "strev_1": "1-month reversal",
    "lowvol": "Low volatility",
}


def compute_all(
    close: pd.DataFrame,
    daily_ret: pd.DataFrame,
    *,
    formation: int = 12,
    skip: int = 1,
    vol_window: int = 252,
    min_daily_obs: int = 120,
) -> dict[str, pd.DataFrame]:
    """All three raw signals in one pass over the price and daily-return panels.

    Raw rather than standardized: standardization needs the eligibility mask, and the
    mask differs between the naive and point-in-time universes the ladder compares.
    """
    return {
        "mom_12_1": mom_12_1(close, formation, skip),
        "strev_1": strev_1(close),
        "lowvol": lowvol(daily_ret, vol_window, min_daily_obs),
    }


def standardize(raw: pd.DataFrame, mask: pd.DataFrame, winsor: float = 0.01) -> pd.DataFrame:
    """Winsorize, rank, and z-score within each date's eligible cross-section only."""
    aligned = raw.reindex(index=mask.index, columns=mask.columns)
    valid = aligned.where(mask)
    lo = valid.quantile(winsor, axis=1)
    hi = valid.quantile(1.0 - winsor, axis=1)
    clipped = valid.clip(lower=lo, upper=hi, axis=0)
    ranks = clipped.rank(axis=1, pct=True)
    mu = ranks.mean(axis=1)
    sd = ranks.std(axis=1, ddof=0).replace(0.0, np.nan)
    return ranks.sub(mu, axis=0).div(sd, axis=0)


def composite(standardized: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Equal-weight blend of the standardized signals."""
    frames = list(standardized.values())
    stacked = pd.concat(frames).groupby(level=0).mean()
    return stacked.reindex(frames[0].index)
