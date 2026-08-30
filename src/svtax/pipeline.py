"""Orchestration: build every panel once, then run the ladder over every signal."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from svtax import costs as C
from svtax import data, panel, signals
from svtax.backtest import BacktestConfig, BacktestResult, run
from svtax.config import Config

SCHEMES = ("decile", "rank", "invvol")
QUANTILES = (5, 10)
# Signal-specific parameter sweeps. `formation` carries the signal's own knob.
SIGNAL_PARAMS: dict[str, tuple[int, ...]] = {
    "mom_12_1": (6, 9, 12),
    "strev_1": (1,),
    "lowvol": (6, 12),
    "composite": (12,),
}


@dataclass
class Study:
    """Every panel the backtests need, built once."""

    cfg: Config
    panels: panel.Panels
    factors: pd.DataFrame
    mask_pit: pd.DataFrame
    mask_naive: pd.DataFrame
    half_spread_bps: pd.DataFrame
    vol: pd.DataFrame
    raw_signals: dict[str, dict[int, pd.DataFrame]]
    coverage: pd.DataFrame


def _raw_signal_variants(p: panel.Panels, cfg: Config) -> dict[str, dict[int, pd.DataFrame]]:
    out: dict[str, dict[int, pd.DataFrame]] = {"mom_12_1": {}, "strev_1": {}, "lowvol": {}}
    for f in SIGNAL_PARAMS["mom_12_1"]:
        out["mom_12_1"][f] = signals.mom_12_1(p.close, formation=f, skip=cfg.skip_months)
    out["strev_1"][1] = signals.strev_1(p.close)
    for months in SIGNAL_PARAMS["lowvol"]:
        window = months * 21
        out["lowvol"][months] = signals.lowvol(
            p.daily_ret, window, min(cfg.min_daily_obs, window // 2)
        )
    return out


def build_study(cache: Path, cfg: Config) -> Study:
    """Load everything from disk and derive the panels shared by all backtests."""
    p = panel.build_panels(cache / "price_parts", cfg.price_start, cfg.sample_end)
    members = data.membership_sets(cache)
    factors = data.load_factors(cache)

    # Both masks apply identical screens; only the membership convention differs.
    mask_pit = panel.universe_mask(
        p,
        members,
        naive=False,
        min_price=cfg.min_price,
        min_daily_obs=cfg.min_daily_obs,
        vol_window=cfg.vol_window,
    )
    mask_naive = panel.universe_mask(
        p,
        members,
        naive=True,
        min_price=cfg.min_price,
        min_daily_obs=cfg.min_daily_obs,
        vol_window=cfg.vol_window,
    )

    half_spread = C.monthly_half_spread_bps(
        p.high,
        p.low,
        p.month_ends,
        floor_bps=cfg.spread_floor_bps,
        cap_bps=cfg.spread_cap_bps,
    )
    vol = p.daily_ret.rolling(cfg.vol_window, min_periods=cfg.min_daily_obs).std()
    vol_me = vol.resample("ME").last().reindex(p.month_ends)

    raw = _raw_signal_variants(p, cfg)
    coverage = panel.coverage_report(p, members)
    return Study(
        cfg=cfg,
        panels=p,
        factors=factors,
        mask_pit=mask_pit,
        mask_naive=mask_naive,
        half_spread_bps=half_spread,
        vol=vol_me,
        raw_signals=raw,
        coverage=coverage,
    )


def standardized(study: Study, signal: str, param: int, *, naive: bool) -> pd.DataFrame:
    """Cross-sectionally standardized signal for one universe. Cached per combination."""
    mask = study.mask_naive if naive else study.mask_pit
    if signal == "composite":
        parts = {
            name: signals.standardize(study.raw_signals[name][SIGNAL_PARAMS[name][-1]], mask)
            for name in ("mom_12_1", "strev_1", "lowvol")
        }
        return signals.composite(parts)
    return signals.standardize(study.raw_signals[signal][param], mask)


def make_runner(study: Study) -> Callable[[BacktestConfig], BacktestResult]:
    """Return a memoized function mapping a config to its backtest result."""
    cache: dict[BacktestConfig, BacktestResult] = {}

    def runner(cfg: BacktestConfig) -> BacktestResult:
        if cfg in cache:
            return cache[cfg]
        mask = study.mask_naive if cfg.naive_universe else study.mask_pit
        z = standardized(study, cfg.signal, cfg.formation, naive=cfg.naive_universe)
        res = run(
            cfg=cfg,
            z=z,
            mask=mask,
            ret_same_close=study.panels.ret_same_close,
            ret_next_open=study.panels.ret_next_open,
            vol=study.vol,
            half_spread_bps=study.half_spread_bps,
            impact_bps=study.cfg.impact_bps,
            borrow_bps=study.cfg.borrow_bps_annual,
            start=study.cfg.sample_start,
            end=study.cfg.sample_end,
        )
        cache[cfg] = res
        return res

    return runner


def grid_for(signal: str) -> list[BacktestConfig]:
    """The pre-registered parameter grid for one signal."""
    return [
        BacktestConfig(signal=signal, scheme=s, n_quantiles=q, formation=f)
        for f in SIGNAL_PARAMS[signal]
        for s in SCHEMES
        for q in QUANTILES
    ]


def total_trials() -> int:
    """Size of the whole pre-registered search: the N the deflated Sharpe deflates by."""
    return sum(len(grid_for(s)) for s in SIGNAL_PARAMS)
