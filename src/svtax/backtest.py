"""The backtest engine. One frozen config in, one result object out.

Nothing downstream recomputes a metric: every number a caller needs is on the
returned dataclass, so two panels of the dashboard cannot silently disagree.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from svtax import costs as C
from svtax import portfolio as P


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """One rung's worth of choices. Hashable, logged verbatim to the trial log."""

    signal: str
    scheme: str = "decile"
    naive_universe: bool = False
    same_close_execution: bool = False
    apply_costs: bool = True
    # Flat per-side cost in bps is the DEFAULT model. Corwin-Schultz is opt-in via
    # None, and is documented as unusable for this universe - see costs.cs_diagnostics.
    flat_cost_bps: float | None = 10.0
    n_quantiles: int = 10
    formation: int = 12
    skip: int = 1


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Monthly series produced by one backtest run."""

    config: BacktestConfig
    gross: pd.Series
    net: pd.Series
    turnover: pd.Series
    cost: pd.Series
    weights: pd.DataFrame

    @property
    def ann_turnover(self) -> float:
        """Mean one-way turnover per rebalance, annualized over the twelve rebalances."""
        return float(self.turnover.mean() * 12.0)


def run(
    *,
    cfg: BacktestConfig,
    z: pd.DataFrame,
    mask: pd.DataFrame,
    ret_same_close: pd.DataFrame,
    ret_next_open: pd.DataFrame,
    vol: pd.DataFrame,
    half_spread_bps: pd.DataFrame,
    impact_bps: float,
    borrow_bps: float,
    start: str,
    end: str,
) -> BacktestResult:
    """Form weights from the signal at t-1 and hold through month t."""
    if cfg.scheme == "decile":
        w = P.decile_weights(z, mask, cfg.n_quantiles)
    elif cfg.scheme == "rank":
        w = P.rank_weights(z, mask)
    elif cfg.scheme == "invvol":
        w = P.inv_vol_weights(z, mask, vol)
    else:  # pragma: no cover - guarded by the config surface
        msg = f"unknown weighting scheme {cfg.scheme!r}"
        raise ValueError(msg)

    w = w.fillna(0.0).loc[start:end]
    fwd = (ret_same_close if cfg.same_close_execution else ret_next_open).reindex_like(w)

    # Weights formed at t-1 earn the return of month t.
    held = w.shift(1).fillna(0.0)
    gross = (held * fwd.fillna(0.0)).sum(axis=1)

    turns, deltas = P.turnover_path(w, ret_same_close.reindex_like(w).fillna(0.0))

    if not cfg.apply_costs:
        cost = pd.Series(0.0, index=gross.index)
    elif cfg.flat_cost_bps is not None:
        cost = turns * 2.0 * cfg.flat_cost_bps / 10_000.0
    else:
        spread_cost = C.trade_cost(deltas, half_spread_bps, impact_bps)
        short_gross = held.clip(upper=0.0).abs().sum(axis=1)
        cost = spread_cost.reindex(gross.index).fillna(0.0) + C.borrow_cost(
            short_gross, borrow_bps
        ).reindex(gross.index).fillna(0.0)

    net = gross - cost.reindex(gross.index).fillna(0.0)
    return BacktestResult(
        config=cfg,
        gross=gross,
        net=net,
        turnover=turns.reindex(gross.index).fillna(0.0),
        cost=cost.reindex(gross.index).fillna(0.0),
        weights=w,
    )
