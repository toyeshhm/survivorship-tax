"""Frozen experiment configuration. Every number that could be tuned lives here."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Final

PIT_CSV: Final = (
    "https://raw.githubusercontent.com/fja05680/sp500/master/"
    "S%26P%20500%20Historical%20Components%20%26%20Changes%20(Updated).csv"
)
FF5_ZIP: Final = "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip"
MOM_ZIP: Final = "F-F_Momentum_Factor_daily_CSV.zip"
FRENCH_BASE: Final = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"


@dataclass(frozen=True, slots=True)
class Config:
    """Immutable run configuration; hashed into every output artifact."""

    seed: int = 20260829
    # Sample. Prices start earlier so the 12-month formation window is warm at start.
    price_start: str = "2009-07-01"
    sample_start: str = "2012-01-31"
    sample_end: str = "2026-06-30"
    # Pre-registered split. The holdout is opened once.
    train_end: str = "2019-12-31"
    # Universe screens applied at each formation date.
    min_price: float = 5.0
    min_monthly_obs: int = 8
    min_daily_obs: int = 120
    # Signal / portfolio parameters.
    formation_months: int = 12
    skip_months: int = 1
    n_quantiles: int = 10
    vol_window: int = 252
    # Cost model.
    # Headline per-side cost for large-cap US equities. Corwin-Schultz was tried and
    # rejected as a level estimate for this universe; see reports/report.md.
    primary_cost_bps: float = 10.0
    borrow_bps_annual: float = 40.0
    impact_bps: float = 2.0
    spread_floor_bps: float = 1.0
    spread_cap_bps: float = 100.0
    cost_grid_bps: tuple[float, ...] = (0.0, 5.0, 10.0, 25.0, 50.0)
    # Inference.
    n_permutations: int = 1000
    n_bootstrap: int = 1000
    cscv_blocks: int = 16

    def hash(self) -> str:
        """Stable short hash of the whole config, stamped into outputs."""
        blob = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()[:12]


DEFAULT: Final = Config()
