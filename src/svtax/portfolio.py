"""Weighting schemes and turnover. Dollar-neutral long-short throughout."""

from __future__ import annotations

import numpy as np
import pandas as pd


def decile_weights(z: pd.DataFrame, mask: pd.DataFrame, n_q: int = 10) -> pd.DataFrame:
    """Equal-weight long the top quantile, short the bottom. 100% gross per side."""
    valid = z.where(mask)
    ranks = valid.rank(axis=1, pct=True)
    long = ranks > (1.0 - 1.0 / n_q)
    short = ranks <= (1.0 / n_q)
    n_long = long.sum(axis=1).replace(0, np.nan)
    n_short = short.sum(axis=1).replace(0, np.nan)
    return long.div(n_long, axis=0).astype(float) - short.div(n_short, axis=0).astype(float)


def rank_weights(z: pd.DataFrame, mask: pd.DataFrame) -> pd.DataFrame:
    """Asness-Moskowitz-Pedersen rank weighting: w proportional to rank minus its mean.

    Uses the whole cross-section instead of discarding the middle 80%, so it is a
    strictly better use of the same information when the signal is monotone.
    """
    valid = z.where(mask)
    ranks = valid.rank(axis=1)
    centered = ranks.sub(ranks.mean(axis=1), axis=0)
    scale = centered.abs().sum(axis=1).replace(0, np.nan) / 2.0
    return centered.div(scale, axis=0)


def inv_vol_weights(z: pd.DataFrame, mask: pd.DataFrame, vol: pd.DataFrame) -> pd.DataFrame:
    """Rank weights scaled by inverse trailing volatility, renormalized per side."""
    base = rank_weights(z, mask)
    inv = (1.0 / vol.reindex_like(base)).replace([np.inf, -np.inf], np.nan)
    raw = base * inv
    longs = raw.clip(lower=0.0)
    shorts = raw.clip(upper=0.0)
    ls = longs.sum(axis=1).replace(0, np.nan)
    ss = shorts.abs().sum(axis=1).replace(0, np.nan)
    return longs.div(ls, axis=0).fillna(0.0) - shorts.abs().div(ss, axis=0).fillna(0.0)


SCHEMES = {"decile": "Decile long-short", "rank": "Rank-weighted", "invvol": "Inverse-vol"}


def drifted_weights(w_prev: pd.Series, ret: pd.Series) -> pd.Series:
    """Weights after a month of price drift, before the next rebalance.

    Turnover must be measured against these, not against last month's targets -
    otherwise it counts drift the strategy never traded, overstating cost.
    """
    grown = w_prev * (1.0 + ret.reindex(w_prev.index).fillna(0.0))
    gross = grown.abs().sum()
    return grown if gross == 0 else grown / gross * w_prev.abs().sum()


def turnover_path(weights: pd.DataFrame, returns: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """One-way turnover per rebalance and the matrix of weight changes traded."""
    idx = weights.index
    deltas = pd.DataFrame(0.0, index=idx, columns=weights.columns)
    turns = pd.Series(0.0, index=idx)
    prev = pd.Series(0.0, index=weights.columns)
    for dt in idx:
        target = weights.loc[dt].fillna(0.0)
        drift = drifted_weights(prev, returns.loc[dt].fillna(0.0)) if prev.abs().sum() else prev
        delta = target - drift
        deltas.loc[dt] = delta
        turns.loc[dt] = float(delta.abs().sum() / 2.0)
        prev = target
    return turns, deltas
