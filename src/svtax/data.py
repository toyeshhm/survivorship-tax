"""Data acquisition: point-in-time index membership, prices, Fama-French factors.

Every source here is free and keyless. The point-in-time membership file is what
makes the survivorship-tax measurement possible at all: it records who was in the
S&P 500 on each date, including the ~600 companies that have since left it.
"""

from __future__ import annotations

import io
import logging
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from svtax.config import FF5_ZIP, FRENCH_BASE, MOM_ZIP, PIT_CSV, Config

log = logging.getLogger(__name__)

_UA = {"User-Agent": "svtax-research/1.0 (academic use)"}

# Ken French's daily CSVs date each data row YYYYMMDD. Any first field of another
# length belongs to the header block or the trailing annual section, not the data.
_DATE_TOKEN_LEN = 8


def _fetch(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return bytes(resp.read())


def load_membership(cache: Path) -> pd.DataFrame:
    """Change-dated S&P 500 membership: one row per change date, comma-joined tickers."""
    f = cache / "membership.csv"
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(_fetch(PIT_CSV))
    df = pd.read_csv(f)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def membership_sets(cache: Path) -> pd.Series:
    """Map each change date to the frozenset of tickers in the index on that date."""
    df = load_membership(cache)
    sets = df["tickers"].map(
        lambda row: frozenset(t.strip() for t in str(row).split(",") if t.strip())
    )
    return pd.Series(sets.to_numpy(), index=pd.DatetimeIndex(df["date"]), name="members")


def month_end_members(cache: Path, cfg: Config) -> pd.Series:
    """Point-in-time membership as of each month end over the sample.

    Forward-fills the change-dated sets onto a month-end grid, so the set attached
    to a formation date is the set that was actually in the index on that date.
    """
    raw = membership_sets(cache)
    grid = pd.date_range(cfg.price_start, cfg.sample_end, freq="ME")
    idx = raw.index.union(grid)
    return raw.reindex(idx).ffill().reindex(grid).dropna()


def ever_members(cache: Path, cfg: Config) -> list[str]:
    """Union of every ticker that was in the index at any point in the price window."""
    raw = membership_sets(cache)
    window = raw[raw.index >= pd.Timestamp(cfg.price_start)]
    union: set[str] = set()
    for s in window:
        union |= set(s)
    # Yahoo uses dashes where the index file uses dots (BRK.B -> BRK-B).
    return sorted({t.replace(".", "-") for t in union})


def load_factors(cache: Path) -> pd.DataFrame:
    """Daily Fama-French 5 factors + momentum, as decimals, from Ken French's library."""
    f = cache / "factors.parquet"
    if f.exists():
        return pd.read_parquet(f)

    def parse(zip_name: str, cols: list[str]) -> pd.DataFrame:
        blob = _fetch(FRENCH_BASE + zip_name)
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            text = z.read(z.namelist()[0]).decode("latin-1")
        rows: list[list[object]] = []
        for line in text.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if (
                len(parts) == len(cols) + 1
                and len(parts[0]) == _DATE_TOKEN_LEN
                and parts[0].isdigit()
            ):
                try:
                    vals = [float(p) for p in parts[1:]]
                except ValueError:
                    continue
                rows.append([pd.Timestamp(parts[0]), *vals])
        out = pd.DataFrame(rows, columns=["date", *cols]).set_index("date")
        return out.astype(float) / 100.0

    ff5 = parse(FF5_ZIP, ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"])
    mom = parse(MOM_ZIP, ["Mom"])
    out = ff5.join(mom, how="inner")
    f.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(f)
    return out
