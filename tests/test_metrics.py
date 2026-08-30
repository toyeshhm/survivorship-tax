"""Metric definitions pinned against hand-computed values."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from svtax import metrics as M


def test_sharpe_matches_hand_computation() -> None:
    r = pd.Series([0.01, -0.02, 0.03, 0.00, 0.015])
    expected = r.mean() / r.std(ddof=0) * np.sqrt(12)
    assert M.sharpe(r) == pytest.approx(expected)


def test_sharpe_is_zero_for_zero_mean() -> None:
    r = pd.Series([0.05, -0.05, 0.05, -0.05])
    assert M.sharpe(r) == pytest.approx(0.0)


def test_sortino_uses_full_n_denominator() -> None:
    """The downside deviation divides by all n, not by the count of losses."""
    r = pd.Series([0.10, 0.10, 0.10, -0.10])
    downside_full_n = np.sqrt(np.mean(np.minimum(r.to_numpy(), 0.0) ** 2))
    assert downside_full_n == pytest.approx(0.05)
    assert M.sortino(r) == pytest.approx(r.mean() / 0.05 * np.sqrt(12))


def test_drawdown_depth_duration_and_recovery() -> None:
    # +25%, then -40% (trough), then recovery above the old peak.
    r = pd.Series(
        [0.25, -0.40, 0.20, 0.60],
        index=pd.date_range("2020-01-31", periods=4, freq="ME"),
    )
    dd = M.drawdown(r)
    assert dd.max_dd == pytest.approx(-0.40)
    assert dd.peak_date == pd.Timestamp("2020-01-31")
    assert dd.trough_date == pd.Timestamp("2020-02-29")
    assert dd.duration_periods == 1
    assert dd.recovery_date == pd.Timestamp("2020-04-30")


def test_cvar_is_at_least_as_severe_as_var() -> None:
    rng = np.random.default_rng(0)
    r = pd.Series(rng.standard_t(4, 500) / 100.0)
    var, cvar = M.var_cvar(r)
    assert cvar <= var < 0
