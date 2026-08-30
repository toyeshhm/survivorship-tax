# Pre-registration

**Committed:** 2026-08-29, before the full study was run.
**Config hash at registration:** `769aa457ab68`

## Honest note on what preceded this document

This is a reconstruction-free pre-registration in the sense that the *design* below
was fixed before any result was produced, but it was not written in ignorance. Two
things were already known when it was committed, and pretending otherwise would
defeat the purpose of the document:

1. **Data coverage had been measured.** Free price data recovers 71.8% of the true
   2012 S&P 500 and 98.7% of the 2026 index. That measurement motivated the study;
   it is not a result of it.
2. **The Corwin-Schultz cost estimator had already been tried and rejected** for this
   universe (see §6). That was an exploratory finding about an *estimator*, not about
   any signal's performance.

No signal's Sharpe, at any rung, was known when this was committed.

## 1. Hypothesis

A standard student factor backtest reports a Sharpe ratio that is inflated by four
methodological shortcuts. The inflation is measurable, and it can be attributed to
each shortcut individually.

**H1.** Replacing backfilled current index constituents with point-in-time membership
reduces measured Sharpe.
**H2.** The reduction from H1 is not uniform in sign across signals: it depends on
whether the surviving names are over- or under-represented in the signal's long leg.
**H3.** Signals decay under transaction costs in order of their turnover, so 1-month
reversal dies before 12-1 momentum.

## 2. Universe

- **Point-in-time (primary):** S&P 500 membership as of each formation date, from the
  change-dated `fja05680/sp500` file.
- **Naive (counterfactual, measured not used):** the index constituents as of
  2026-06-30, applied to every historical date.
- **Screens at each formation date:** price > \$5, at least 120 non-missing daily
  returns in the trailing 252 days.

## 3. Sample and split

- **Full sample:** 2012-01-31 to 2026-06-30 (174 months).
- **Training:** 2012-01-31 to 2019-12-31.
- **Holdout:** 2020-01-31 to 2026-06-30. Opened once, after parameters were selected
  on training data only. Every look at the holdout is logged as a trial.

## 4. Signals

| Signal | Definition | Mechanism |
|---|---|---|
| `mom_12_1` | Return t−12 to t−2, skipping t−1 | Under-reaction; skip purges reversal and bid-ask bounce |
| `strev_1` | Negative of month t−1 return | Compensation for providing liquidity |
| `lowvol` | Negative trailing 252d volatility | Leverage-constrained investors overpay for high beta |
| `composite` | Equal-weight blend of the three z-scores | Diversification across mechanisms |

Fundamental signals (book-to-market, gross profitability) are **out of scope**: they
require point-in-time SEC filings keyed on filing date, which is a separate data
pipeline. Their absence is a stated limitation, not a silent omission.

## 5. Parameter grid (pre-registered, N = 42)

- Formation windows: momentum {6, 9, 12} months; low-vol {6, 12} months; reversal {1}.
- Weighting schemes: {decile, rank, inverse-vol}.
- Quantiles: {5, 10}.

Every cell is run and logged to `results/trials.csv` with its git SHA and config hash,
whether or not it appears in any figure.

## 6. Cost model

**Primary:** flat cost per side, swept over {0, 2, 5, 10, 15, 20, 25, 30, 40, 50} bps,
with the ladder's cost rung charged at **10 bps per side** plus a 40 bp/yr borrow
accrual on the short leg. The **break-even cost** — the round-trip cost that exactly
erases the gross edge — is reported for every sleeve as the assumption-free statistic.

**Rejected before use:** the Corwin-Schultz (2012) high-low spread estimator. On this
universe 71.7% of name-months produce a non-positive estimate, and the cross-sectional
rank correlation between the estimate and realized volatility is −0.10 — the wrong
sign. The true effective spread of an S&P 500 name sits below what daily high-low data
can resolve. The estimator is retained in the codebase and its diagnostics are
reported, because a cost model that was tried and failed is a result.

## 7. Primary metric and decision rule

**Primary metric:** annualized Sharpe of the net monthly return of the long-short
spread.

**A signal is declared surviving if and only if**, on the holdout, at 10 bps per side,
using the parameters chosen on training data: net Sharpe > 0 **and** the Newey-West
t-statistic on alpha versus FF5+UMD exceeds 2.0.

The Deflated Sharpe Ratio against the logged trial count is reported **regardless of
the answer**, as is the probability of backtest overfitting.

## 8. Power, stated before the result

With 174 monthly observations the smallest annualized Sharpe detectable at 95%
confidence is **0.43**. Any null result is reported against this bound: this study
cannot distinguish a true Sharpe of 0.2 from zero, and will say so rather than
claiming a signal does not exist.

## 9. Negative controls, run whether they pass or fail

1. **Placebo signal** — Gaussian noise through the full construction; must earn nothing.
2. **Stale signal** — signal lagged two extra months; edge must disappear.
3. **Leakage probe** — signal shifted forward; performance must jump, proving the
   look-ahead guard is a real constraint and not a test that cannot fail.
4. **Within-date permutation** — the signal is shuffled across names within each date,
   1,000 draws, full pipeline including costs.

## AMENDMENTS

None.
