"""Synthetic panels with a known, planted signal-return relationship."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pytest

N_NAMES = 60
N_MONTHS = 150
BETA = 0.02


@dataclass(frozen=True)
class Synthetic:
    z: pd.DataFrame
    mask: pd.DataFrame
    ret: pd.DataFrame
    vol: pd.DataFrame
    spread: pd.DataFrame


@pytest.fixture
def synthetic() -> Synthetic:
    """A panel where month t's return is driven by month t-1's signal, by construction.

    Any engine that scores well here without the shift is reading the future.
    """
    rng = np.random.default_rng(20260829)
    idx = pd.date_range("2012-01-31", periods=N_MONTHS, freq="ME")
    cols = [f"T{i:03d}" for i in range(N_NAMES)]

    raw = rng.standard_normal((N_MONTHS, N_NAMES))
    z = pd.DataFrame(raw, index=idx, columns=cols)
    z = z.sub(z.mean(axis=1), axis=0).div(z.std(axis=1, ddof=0), axis=0)

    noise = rng.standard_normal((N_MONTHS, N_NAMES)) * 0.06
    # Return in month t is explained by the signal known at the end of month t-1.
    ret = pd.DataFrame(noise, index=idx, columns=cols) + BETA * z.shift(1).fillna(0.0)

    vol = pd.DataFrame(0.02, index=idx, columns=cols)
    spread = pd.DataFrame(5.0, index=idx, columns=cols)
    mask = pd.DataFrame(True, index=idx, columns=cols)
    return Synthetic(z=z, mask=mask, ret=ret, vol=vol, spread=spread)


@pytest.fixture
def contemporaneous() -> Synthetic:
    """A panel where the signal explains the SAME month's return, and nothing later.

    An honest engine must earn nothing here: the only way to profit is to trade on
    information that was not available when the position had to be formed.
    """
    rng = np.random.default_rng(1234)
    idx = pd.date_range("2012-01-31", periods=N_MONTHS, freq="ME")
    cols = [f"T{i:03d}" for i in range(N_NAMES)]

    raw = rng.standard_normal((N_MONTHS, N_NAMES))
    z = pd.DataFrame(raw, index=idx, columns=cols)
    z = z.sub(z.mean(axis=1), axis=0).div(z.std(axis=1, ddof=0), axis=0)

    noise = rng.standard_normal((N_MONTHS, N_NAMES)) * 0.06
    ret = pd.DataFrame(noise, index=idx, columns=cols) + BETA * z

    vol = pd.DataFrame(0.02, index=idx, columns=cols)
    spread = pd.DataFrame(5.0, index=idx, columns=cols)
    mask = pd.DataFrame(True, index=idx, columns=cols)
    return Synthetic(z=z, mask=mask, ret=ret, vol=vol, spread=spread)
