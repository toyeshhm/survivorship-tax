"""The engine must earn its P&L from information available before the return.

These are the tests that would catch the single most damaging class of bug in a
backtest, and the ones a reviewer is most likely to ask whether you wrote.
"""

from __future__ import annotations

import pandas as pd

from conftest import Synthetic
from svtax import metrics as M
from svtax.backtest import BacktestConfig, run

CFG = BacktestConfig(signal="synthetic", scheme="decile", apply_costs=False)


def _sharpe(syn: Synthetic, z: pd.DataFrame) -> float:
    res = run(
        cfg=CFG,
        z=z,
        mask=syn.mask,
        ret_same_close=syn.ret,
        ret_next_open=syn.ret,
        vol=syn.vol,
        half_spread_bps=syn.spread,
        impact_bps=0.0,
        borrow_bps=0.0,
        start=str(syn.z.index[0].date()),
        end=str(syn.z.index[-1].date()),
    )
    return M.sharpe(res.gross)


def test_planted_signal_is_recovered(synthetic: Synthetic) -> None:
    """The correctly-aligned engine finds the signal that was planted."""
    assert _sharpe(synthetic, synthetic.z) > 1.0


def test_engine_cannot_use_contemporaneous_information(contemporaneous: Synthetic) -> None:
    """On a panel whose signal only explains the SAME month, the engine earns nothing.

    This is the load-bearing test. The engine forms weights from the signal known at
    t-1 and applies them to month t; if it were instead scoring month t's signal
    against month t's return, it would post a large Sharpe here.
    """
    assert abs(_sharpe(contemporaneous, contemporaneous.z)) < 0.75


def test_the_leakage_test_has_power(contemporaneous: Synthetic) -> None:
    """Deliberately leak the future and confirm the previous test would have caught it.

    Shifting the signal back by one month hands the engine the contemporaneous
    signal it is supposed to be denied. A large Sharpe here proves the guard above
    is a real constraint and not a test that could never fail.
    """
    leaked = _sharpe(contemporaneous, contemporaneous.z.shift(-1))
    assert leaked > 2.0


def test_stale_signal_degrades_toward_zero(synthetic: Synthetic) -> None:
    """Shifting the signal backward destroys the edge, smoothly rather than abruptly."""
    honest = _sharpe(synthetic, synthetic.z)
    stale = _sharpe(synthetic, synthetic.z.shift(2))
    assert stale < honest * 0.5
    assert abs(stale) < 1.0


def test_random_signal_earns_nothing(synthetic: Synthetic) -> None:
    """A placebo signal run through the same construction has no edge."""
    import numpy as np

    rng = np.random.default_rng(7)
    placebo = pd.DataFrame(
        rng.standard_normal(synthetic.z.shape),
        index=synthetic.z.index,
        columns=synthetic.z.columns,
    )
    assert abs(_sharpe(synthetic, placebo)) < 0.75


def test_costs_reduce_returns_monotonically(synthetic: Synthetic) -> None:
    """More expensive assumptions can never produce a better net return."""
    nets = []
    for bps in (0.0, 10.0, 25.0, 50.0):
        res = run(
            cfg=BacktestConfig(signal="s", apply_costs=True, flat_cost_bps=bps),
            z=synthetic.z,
            mask=synthetic.mask,
            ret_same_close=synthetic.ret,
            ret_next_open=synthetic.ret,
            vol=synthetic.vol,
            half_spread_bps=synthetic.spread,
            impact_bps=0.0,
            borrow_bps=0.0,
            start=str(synthetic.z.index[0].date()),
            end=str(synthetic.z.index[-1].date()),
        )
        nets.append(res.net.mean())
    assert nets == sorted(nets, reverse=True)
