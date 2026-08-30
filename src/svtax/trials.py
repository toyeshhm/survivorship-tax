"""The trial log. Every backtest that is run is recorded, so N is a fact, not a guess.

The Deflated Sharpe Ratio needs the number of configurations searched and the spread
of their Sharpes. Both are only knowable if the log is written as the search happens.
"""

from __future__ import annotations

import subprocess
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from svtax import metrics as M
from svtax.backtest import BacktestConfig, BacktestResult


def git_sha() -> str:
    """Short SHA of the current commit, stamped into every logged trial."""
    try:
        out = subprocess.run(
            ["/usr/bin/env", "git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return "unknown"


class TrialLog:
    """Accumulates one row and one return series per configuration evaluated."""

    def __init__(self, config_hash: str, seed: int) -> None:
        """Start an empty log stamped with the run's config hash, seed, and git SHA."""
        self.config_hash = config_hash
        self.seed = seed
        self.sha = git_sha()
        self._rows: list[dict[str, object]] = []
        self._returns: dict[str, pd.Series] = {}

    def record(self, res: BacktestResult, train_end: str, label: str) -> None:
        """Append one configuration's summary row and its net return series."""
        cfg: BacktestConfig = res.config
        net = res.net
        self._rows.append(
            {
                "label": label,
                "git_sha": self.sha,
                "config_hash": self.config_hash,
                "seed": self.seed,
                **asdict(cfg),
                "sharpe_full": M.sharpe(net),
                "sharpe_is": M.sharpe(net.loc[:train_end]),
                "sharpe_oos": M.sharpe(net.loc[train_end:].iloc[1:]),
                "ann_turnover": res.ann_turnover,
                "mean_monthly_gross": float(res.gross.mean()),
            }
        )
        self._returns[label] = net

    @property
    def n_trials(self) -> int:
        """Number of configurations evaluated so far - the N in the deflated Sharpe."""
        return len(self._rows)

    def frame(self) -> pd.DataFrame:
        """One row per trial."""
        return pd.DataFrame(self._rows)

    def returns_matrix(self) -> pd.DataFrame:
        """T x N matrix of net monthly returns, the input to CSCV."""
        return pd.DataFrame(self._returns)

    def sharpes(self) -> pd.Series:
        """Full-sample Sharpe of every trial, the input to the deflated Sharpe."""
        return self.frame()["sharpe_full"]

    def write(self, results_dir: Path) -> None:
        """Persist the log and the per-trial return series as evidence."""
        results_dir.mkdir(parents=True, exist_ok=True)
        self.frame().to_csv(results_dir / "trials.csv", index=False)
        self.returns_matrix().to_parquet(results_dir / "trial_returns.parquet")
