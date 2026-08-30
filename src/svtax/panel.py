"""Assemble raw price parts into aligned panels and the two return conventions.

The two return conventions are the heart of the execution-lag rung of the ladder:

* `same_close` - the signal is computed from month-end close t-1 and the position
  is assumed filled at that same close. Impossible in practice; it is what a naive
  backtest silently does.
* `next_open`  - the position is filled at the open of the first trading day of
  month t, forfeiting the overnight gap. This is what an honest backtest does.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pandas as pd


@dataclass(frozen=True, slots=True)
class Panels:
    """Aligned daily bars plus the derived monthly return conventions."""

    close: pd.DataFrame
    high: pd.DataFrame
    low: pd.DataFrame
    open_: pd.DataFrame
    daily_ret: pd.DataFrame
    month_ends: pd.DatetimeIndex
    ret_same_close: pd.DataFrame
    ret_next_open: pd.DataFrame

    @property
    def tickers(self) -> list[str]:
        """Column order shared by every panel here, in the order the parts were stacked."""
        return list(self.close.columns)


def _stack(parts_dir: Path, field: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for f in sorted(parts_dir.glob("*.parquet")):
        df = pd.read_parquet(f)
        if df.empty or field not in df.columns.get_level_values(0):
            continue
        # Selecting the outer level of a MultiIndex column yields a frame of the
        # tickers under it; the stubs only describe the single-column case.
        frames.append(cast("pd.DataFrame", df[field]))
    if not frames:
        msg = f"no price parts found for field {field!r} in {parts_dir}"
        raise FileNotFoundError(msg)
    out = pd.concat(frames, axis=1).sort_index()
    return out.loc[:, ~out.columns.duplicated()]


def build_panels(parts_dir: Path, start: str, end: str, min_obs: int = 250) -> Panels:
    """Load all parts, drop thinly-traded names, and derive both return conventions."""
    close = _stack(parts_dir, "Close")
    keep = close.columns[close.notna().sum() >= min_obs]
    close = close[keep].loc[start:end]
    high = _stack(parts_dir, "High")[keep].loc[start:end]
    low = _stack(parts_dir, "Low")[keep].loc[start:end]
    open_ = _stack(parts_dir, "Open")[keep].loc[start:end]

    daily_ret = close.pct_change(fill_method=None)

    # Month-end close panel, and the first trading open of each month.
    close_me = close.resample("ME").last()
    open_first = open_.resample("ME").first()

    ret_same_close = close_me.pct_change(fill_method=None)
    # Fill at the first open of month t, hold to the close of month t.
    ret_next_open = close_me / open_first - 1.0

    return Panels(
        close=close,
        high=high,
        low=low,
        open_=open_,
        daily_ret=daily_ret,
        month_ends=pd.DatetimeIndex(close_me.index),
        ret_same_close=ret_same_close,
        ret_next_open=ret_next_open,
    )


def universe_mask(
    panels: Panels,
    members_by_date: pd.Series,
    *,
    naive: bool,
    min_price: float,
    min_daily_obs: int,
    vol_window: int,
) -> pd.DataFrame:
    """Boolean (month-end x ticker) mask of names eligible at each formation date.

    When `naive` is True the final month's membership is applied to every historical
    date - the backfilled-current-constituents shortcut this study is measuring.
    """
    idx = panels.month_ends
    cols = panels.close.columns
    mask = pd.DataFrame(data=False, index=idx, columns=cols)

    aligned = members_by_date.reindex(idx).ffill()
    final = aligned.dropna().iloc[-1]

    close_me = panels.close.resample("ME").last().reindex(idx)
    obs = panels.daily_ret.notna().rolling(vol_window, min_periods=1).sum()
    obs_me = obs.resample("ME").last().reindex(idx)

    for dt in idx:
        members = final if naive else aligned.get(dt)
        if members is None or not isinstance(members, frozenset):
            continue
        # Index file uses dots, Yahoo uses dashes.
        names = {t.replace(".", "-") for t in members}
        eligible = cols.isin(names)
        priced = (close_me.loc[dt] > min_price).to_numpy(dtype=bool)
        enough = (obs_me.loc[dt] >= min_daily_obs).to_numpy(dtype=bool)
        mask.loc[dt] = eligible & priced & enough
    return mask


def coverage_report(panels: Panels, members_by_date: pd.Series) -> pd.DataFrame:
    """How much of the true index we can actually price, by date.

    This is the direct measurement of the free-data survivorship hole: names that
    left the index are largely absent from the free price source.
    """
    rows: list[dict[str, object]] = []
    have = set(panels.close.columns)
    for dt, members in members_by_date.items():
        if not isinstance(members, frozenset):
            continue
        names = {t.replace(".", "-") for t in members}
        rows.append(
            {
                "date": dt,
                "n_true": len(names),
                "n_available": len(names & have),
                "coverage": len(names & have) / max(len(names), 1),
            }
        )
    return pd.DataFrame(rows).set_index("date")
