"""Fetch adjusted OHLC bars for every ever-member of the index. Resumable by batch."""

from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import yfinance as yf

from svtax import data
from svtax.config import DEFAULT

warnings.filterwarnings("ignore")

CACHE = Path("data/raw")
PARTS = CACHE / "price_parts"
FIELDS = ["Open", "High", "Low", "Close"]
BATCH = 40


def main() -> None:
    """Download one parquet part per batch of tickers, skipping parts already on disk."""
    PARTS.mkdir(parents=True, exist_ok=True)
    yf.set_tz_cache_location(str(CACHE / "yf_tz"))
    tickers = data.ever_members(CACHE, DEFAULT)
    print(f"ever-members: {len(tickers)}", flush=True)

    for i in range(0, len(tickers), BATCH):
        chunk = tickers[i : i + BATCH]
        out = PARTS / f"p{i:05d}.parquet"
        if out.exists():
            continue
        try:
            raw = yf.download(
                chunk,
                start=DEFAULT.price_start,
                end="2026-07-01",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            if raw is None or raw.empty:
                pd.DataFrame().to_parquet(out)
                print(f"[{i + len(chunk)}/{len(tickers)}] empty", flush=True)
                continue
            frames = []
            for field in FIELDS:
                sub = raw[field].dropna(axis=1, how="all")
                sub.columns = pd.MultiIndex.from_product([[field], sub.columns])
                frames.append(sub)
            panel = pd.concat(frames, axis=1)
            panel.to_parquet(out)
            n_ok = panel["Close"].shape[1]
            print(f"[{i + len(chunk)}/{len(tickers)}] kept {n_ok}/{len(chunk)}", flush=True)
        except Exception as exc:  # noqa: BLE001 - batch failure must not abort the run
            pd.DataFrame().to_parquet(out)
            print(f"[{i + len(chunk)}] FAIL {type(exc).__name__}: {exc}", flush=True)
        time.sleep(0.3)
    print("FETCH DONE", flush=True)


if __name__ == "__main__":
    main()
