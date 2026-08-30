# The Survivorship Tax

**How much of a quantitative factor backtest is signal, and how much is the shortcuts
that produced it?**

This study rebuilds the same cross-sectional equity signals five times over a
point-in-time S&P 500 universe (2012-01 to 2026-06, 174 months), removing one standard
methodological shortcut per rung, and reports what each shortcut was worth in Sharpe.

**→ [Live dashboard](https://survivorship-tax.vercel.app) · [Full research note](reports/report.md) · [Pre-registration](docs/preregistration.md)**

---

## The result

On the same sample, with the same parameters, 12-1 momentum's Sharpe ratio falls from
**0.378 to 0.084** as four shortcuts are removed. **78% of the headline was method, not
signal.**

| Rung | Shortcut removed | Sharpe | ΔSharpe | Share of decay |
|---|---|---:|---:|---:|
| L0 | *(naive baseline)* | 0.378 | — | — |
| L1 | Backfilled current constituents | 0.177 | −0.201 | **68%** |
| L2 | Same-close execution | 0.155 | −0.022 | 7% |
| L3 | Zero transaction costs | 0.084 | −0.071 | 24% |

Universe construction alone accounts for more of the decay than costs and execution
combined. It is also the shortcut most often taken silently: pulling today's index
members is the path of least resistance in every free data API.

### Two findings that were not expected

**1. Survivorship bias is not uniformly inflationary.** It has a sign, and the sign
depends on the signal.

| Signal | L0 naive | L1 point-in-time | Δ |
|---|---:|---:|---:|
| 12-1 Momentum | 0.378 | 0.177 | −0.201 |
| 1-Month Reversal | 0.018 | 0.108 | +0.089 |
| Low Volatility | −0.718 | −0.261 | **+0.457** |
| Equal-Weight Composite | −0.417 | −0.079 | +0.338 |

Backfilling the index inflates momentum but *deflates* low volatility, because the
survivors added to a backfilled universe are disproportionately high-volatility winners,
which is exactly what a low-volatility signal is short. "Survivorship bias inflates
returns" is the wrong lesson.

**2. Nothing survives.** After honest construction, no signal shows significant alpha.
The momentum sleeve loads **1.15 on the published UMD factor** with an R² of 0.63 and an
alpha of −1.4% at t = −0.43. It is a slightly worse-executed copy of a factor anyone can
buy.

The study says so, and also says why that conclusion is weak: with 174 months, the
smallest annualized Sharpe detectable at 95% confidence is **0.43**. The honest estimate
is well below that. The correct conclusion is *not proven*, not *disproven*.

## Why the universe matters this much

Free price data does not merely omit a few delisted names. Of the companies genuinely in
the S&P 500 in 2012, only **71.9%** can still be priced today; by 2026 that reaches
**98.7%**. Across the sample an average of **104 index members per month** are invisible.

The upward slope *is* the bias. Point-in-time membership fixes *who* is in the universe;
it cannot resurrect prices the data source has erased, so every number here is a **lower
bound** on the true tax.

## Rigor

| | |
|---|---|
| Pre-registered | Hypotheses, grid, split and decision rule committed before the run |
| Holdout | 78 months, opened once, after parameters were fixed on training data |
| Trials logged | All 42 configurations in [`results/trials.csv`](results/trials.csv), with git SHA and config hash |
| Permutation test | Within-date signal permutation, 1,000 draws, p = **0.268** |
| Backtest overfitting | CSCV, PBO = **0.53**, in-sample→out-of-sample slope = **−0.43** |
| Deflated Sharpe | E[max Sharpe] under the null over 42 trials = **0.33**, which exceeds anything found |
| Attribution | FF5 + UMD, Newey-West errors at 5 lags |
| Negative controls | Gaussian placebo = 0.050; permutation null mean = 0.001 |
| Power | Minimum detectable Sharpe stated up front: **0.43** |

### Two things that did not work, reported rather than buried

**The Corwin-Schultz cost estimator.** Implemented first, then rejected: on this universe
**71.7% of name-months return a non-positive estimate**, and its cross-sectional rank
correlation with realized volatility comes out *negative*. The true effective spread of an
S&P 500 name sits below what daily high-low bars can resolve. The code and diagnostics are
kept, because an estimator that fails is a result. Costs are instead swept over a flat
grid, with **break-even cost** reported as the assumption-free statistic.

**The first permutation test was wrong.** Permuting the signal destroys the month-to-month
persistence of the weights, which roughly doubles turnover. Charging costs then compares a
low-turnover real signal against high-turnover random ones, so the test measures the cost
model rather than the signal. It reported p = 0.002. Run correctly on gross returns, the
same test reports **p = 0.268**, and the null recentres from −0.77 to 0.001. The
"significant" result was an artifact of the test.

## Reproduce

```bash
make setup     # uv venv + dependencies
make data      # fetch prices, membership, Fama-French factors (~3 min)
make research  # run the full study, write results/ (~2.5 min)
make export    # write dashboard JSON
make web       # build the static site
```

`make check` runs ruff, mypy `--strict`, and pytest. `make all` runs everything in order.
The Makefile pins `PYTHONHASHSEED` and single-threads BLAS, so a clean checkout run twice
produces an identical `results/` tree.

## Repository tour

```
src/svtax/
  config.py      frozen run configuration, hashed into every output
  data.py        point-in-time membership, prices, Fama-French factors
  panel.py       aligned panels; the two execution conventions; coverage measurement
  signals.py     the three signals, each with its economic mechanism
  portfolio.py   weighting schemes; turnover against drifted weights
  costs.py       Corwin-Schultz (documented failure) + break-even
  backtest.py    the engine: one frozen config in, one result object out
  ladder.py      the five rungs - the project's headline object
  stats.py       PSR, MinTRL, Deflated Sharpe, CSCV/PBO, Harvey-Liu haircut
  inference.py   within-date permutation, stationary bootstrap
  risk.py        FF5+UMD attribution with HAC errors; Daniel-Moskowitz crash regression
tests/
  test_no_lookahead.py   the load-bearing tests: the engine must not see the future
  test_metrics.py        every metric pinned to a hand-computed value
```

`stats.py` is written from the source papers rather than imported from a library, so every
number in the multiple-testing panel can be defended line by line.

## Limitations, with the direction of each bias

- **Delisted prices are unavailable** at any free source. The measured tax therefore
  *understates* the true one.
- **Fundamental signals are out of scope.** Book-to-market and gross profitability need
  filing-date-accurate SEC data, which is a separate pipeline.
- **Large-cap US only.** Costs here are the friendliest they get; the tax would be larger
  in small caps.
- **The study is underpowered** for the question of whether a small true alpha exists, and
  says so rather than claiming a null.

## License

MIT. Data is fetched at build time and never redistributed.
