# The Survivorship Tax: itemizing what a factor backtest owes to its shortcuts

**Sample:** 2012-01-31 to 2026-06-30, 174 months. **Universe:** S&P 500, point-in-time.
**Config hash:** `4e9507429916`. Seed 20260829. Runtime 111.4s.

---

## 1. Abstract

A standard cross-sectional equity backtest was rebuilt five times over one sample, removing one methodological shortcut per rung, so each shortcut's contribution to the reported Sharpe ratio could be priced separately. For 12-1 momentum the Sharpe falls from 0.378 with a backfilled universe, same-close execution and zero costs, to 0.084 once membership is point-in-time, fills happen at the next open, and 10 bps per side is charged. Universe construction alone accounts for 0.201 of that 0.294 decline; execution for 0.022; transaction costs for 0.071.

Two results were not anticipated. First, the sign of the survivorship effect is signal-dependent: backfilling inflates momentum by 0.201 Sharpe but *deflates* low volatility by 0.457, because the names a backfilled universe silently adds are disproportionately high-volatility survivors that a low-volatility signal is short. Second, nothing survives the honest construction: the momentum sleeve loads 1.15 on the published UMD factor with an R-squared of 0.63 and an annual alpha of -1.4% at t = -0.43.

That second conclusion is weak by construction, and the study says so before reporting it. With 174 months, the smallest annualized Sharpe detectable at 95% confidence is **0.43**. Every honest estimate here sits well below that bound. The correct reading is *not detected at this sample size*, not *does not exist*.

## 2. Motivation

The naive backtest is the default because each of its shortcuts is the path of least resistance, not a decision anyone makes. Pull an index's current members from a free API and you have a ticker list in one line; nothing in it announces that it is the 2026 list applied to 2012. Multiply a month-end signal by next month's close-to-close return and nothing announces that the fill price had already printed. Leaving costs out shortens the code, and the best cell of a grid is the highest number you saw.

None of these is dishonest. Each is invisible, which is the property worth measuring: a shortcut that announced itself would be caught in review, while one that does not compounds silently with the other three. Design, split, grid, cost model, decision rule and power bound were committed in `docs/preregistration.md` before the run, which also records the two things already known then: coverage had been measured, and Corwin-Schultz had been tried and rejected.

## 3. Data and the point-in-time universe

Membership comes from the change-dated `fja05680/sp500` file, forward-filled onto a month-end grid, so each formation date sees the set actually in the index then, including companies that have since left. The naive counterfactual applies the final set to every historical date, which is what querying current membership produces. That fixes *who* belongs in the universe, not what the price source still carries.

| Year | True members | Priceable | Coverage |
|---|---:|---:|---:|
| 2012 | 496.9 | 357.2 | 71.9% |
| 2014 | 498.1 | 370.6 | 74.4% |
| 2016 | 505.3 | 398.1 | 78.8% |
| 2018 | 505.6 | 419.1 | 82.9% |
| 2020 | 505.2 | 446.0 | 88.3% |
| 2022 | 503.8 | 465.7 | 92.4% |
| 2024 | 503.1 | 483.5 | 96.1% |
| 2026 | 503.2 | 496.8 | 98.7% |

Mean coverage is 79.3%, so **103.6 index members per month are invisible**. After screens the mean eligible point-in-time universe is 402.1 names per month, against 469.0 naive.

The upward slope is the bias: distant history is missing a quarter of its constituents, and that quarter is the companies that stopped existing. Point-in-time membership cannot restore prices the source erased, and those erasures fall in exactly the direction that would make the tax larger, so every measurement here is a **lower bound**.

## 4. Signals

**12-1 momentum** (`mom_12_1`): return from t-12 to t-2, skipping the most recent month, which purges short-horizon reversal and bid-ask bounce. Mechanism: under-reaction and delayed diffusion of information (Jegadeesh and Titman 1993, Carhart 1997). On the other side is the investor slow to update on public information, and, in the crash regime, one compensated for the option-like downside the strategy carries when the market rebounds out of a bear state.

**1-month reversal** (`strev_1`): the negative of last month's return. Mechanism: compensation for providing liquidity, the counterparty being a forced or impatient seller. Highest-turnover signal here, so it tests hypothesis H3, that signals die under costs in turnover order.

**Low volatility** (`lowvol`): the negative of trailing 252-day realized volatility. Mechanism: leverage-constrained investors bid up high beta because they cannot lever low beta (Frazzini and Pedersen 2014); the counterparty is a mandate that forbids leverage and buys beta instead.

An equal-weight composite is a fourth sleeve. Standardization is cross-sectional and per-date (winsorize at 1%, rank, z-score) behind the eligibility mask, which differs between the two universes; there is no time-series normalization anywhere, since a full-sample moment would leak the future.

**Fundamental signals are out of scope.** Book-to-market and gross profitability (Fama and French 2015, Novy-Marx 2013) need SEC filings keyed on filing date, and running them on period-end dates would introduce the exact look-ahead this study measures.

## 5. Backtest protocol

| Element | Convention |
|---|---|
| Universe | Point-in-time membership at each formation date; price > $5, 120+ non-missing daily returns in trailing 252 days |
| Formation | Signal through the close of t-1; winsorized at 1%, ranked, z-scored within that date's eligible cross-section |
| Execution (honest) | Formed at close of t-1, filled at the first open of t, held to the close of t; the overnight and opening gap is forfeited |
| Execution (naive) | Same-close: filled at the close the signal came from, month t measured close to close |
| Holding period | One month, full rebalance at each month end |
| Weighting | Decile (equal-weight top and bottom quantile, 100% gross per side), rank, inverse-vol. Dollar-neutral long-short |
| Turnover | One-way: half the sum of absolute weight changes, against **drifted** pre-rebalance weights, so drift never traded is not counted |
| Cost model | Flat per-side rate on every dollar traded; primary 10 bps, swept 0 to 50, with break-even alongside |

Drift for turnover always uses close-to-close returns, keeping it consistent across execution conventions. The 40 bp/yr borrow accrual is charged only in the per-name branch, so the primary path's net numbers are slightly optimistic in a way that changes no ordering.

## 6. The ladder

Five nested configurations. L1 through L3 keep the parameters that won at L0, so each delta is the shortcut's price rather than a reselection's.

- **L0 Naive.** Backfilled current constituents, same-close fill, zero costs, best grid cell over the full sample.
- **L1.** Point-in-time membership at each formation date.
- **L2.** Fill at the next open.
- **L3.** 10 bps per side. Last rung whose sample and reporting discipline match L0.
- **L4.** Parameters chosen on training data only (2012-01 to 2019-12), reported on the 78-month holdout, Sharpe deflated for configurations searched.

### 6.1 The decomposition, 12-1 momentum

| Rung | Shortcut removed | Sharpe | Delta | Months | Share of L0-L3 decay |
|---|---|---:|---:|---:|---:|
| L0 | *(naive baseline)* | 0.378 | | 174 | |
| L1 | Backfilled constituents | 0.177 | -0.201 | 174 | 68% |
| L2 | Same-close execution | 0.155 | -0.022 | 174 | 7% |
| L3 | Zero transaction costs | 0.084 | -0.071 | 174 | 24% |
| L4 | Full-sample reporting | 0.167 | +0.083 | 78 | see section 7 |

Total decay L0 to L4 is 0.211; L0 to L3, the like-for-like comparison, is 0.294, or 78% of the naive headline. Universe construction is worth three times execution and costs combined, and it is the cheapest shortcut to take: a reviewer can ask what cost assumption was used, but asking whether the ticker list was point-in-time requires knowing the question exists.

### 6.2 The same ladder, all four sleeves

| Signal | L0 | L1 | L2 | L3 | L4 (78m) | L0 to L1 |
|---|---:|---:|---:|---:|---:|---:|
| 12-1 Momentum | 0.378 | 0.177 | 0.155 | 0.084 | 0.167 | **-0.201** |
| 1-Month Reversal | 0.018 | 0.108 | 0.157 | -0.174 | -0.547 | **+0.089** |
| Low Volatility | -0.718 | -0.261 | -0.192 | -0.227 | -0.545 | **+0.457** |
| Equal-Weight Composite | -0.417 | -0.079 | -0.033 | -0.214 | -0.637 | **+0.338** |

Three of the four L0-to-L1 deltas are positive: the shortcut made three of these four sleeves look *worse*.

The naive universe is the final membership list applied backwards, so the names it adds to 2012 are the companies admitted between 2012 and 2026, the ones that grew into the index: high-return, and over that period high-volatility. A low-volatility signal is by construction short high-volatility names, so backfilling loads its short leg with survivors that subsequently outperformed, and removing the shortcut returns 0.457 Sharpe. Momentum's long leg holds those same survivors, so backfilling flatters it and removing the shortcut takes 0.201 away.

This is hypothesis H2: the sign is set by whether survivors concentrate in the long leg or the short leg. "Survivorship bias inflates returns" is the wrong summary; it inflates returns *for signals long survivors* and does the opposite for signals short them.

The L2-to-L3 column confirms H3. Reversal, the highest-turnover sleeve, goes from the best L2 Sharpe (0.157) to the worst L3 Sharpe (-0.174), losing 0.331 to a 10 bps charge, while momentum loses 0.071 and low volatility 0.035.

## 7. The L3 to L4 step is not clean

L4 changes two things at once: the reporting discipline and the sample period (78 months instead of 174), so its delta is not attributable to the discipline alone. The `period_effect` block isolates the period, holding one configuration (each signal's first grid cell, costs applied) across three windows.

| Signal | Full sample | Train (2012-2019) | Holdout (2020-2026) |
|---|---:|---:|---:|
| 12-1 Momentum | 0.012 | -0.075 | 0.090 |
| 1-Month Reversal | -0.167 | 0.197 | -0.444 |
| Low Volatility | -0.279 | 0.033 | -0.547 |
| Equal-Weight Composite | -0.234 | 0.184 | -0.611 |

At fixed parameters and discipline, the holdout is worth about +0.077 Sharpe to momentum relative to the full sample, and between -0.27 and -0.38 to the other three. Momentum's L4 delta is +0.083, so nearly all of it is period, not discipline; the large negative deltas elsewhere (-0.373, -0.318, -0.423) are likewise substantially a post-2020 period hostile to those sleeves. The comparison is approximate, since `period_effect` uses each signal's first grid cell while L3 uses the cell that won at L0.

**L3 is the like-for-like number:** same sample, parameters and reporting rule as L0. L4 is reported because the holdout discipline is worth reporting, not because its delta reads as a fifth shortcut's price.

## 8. Costs

The cost rung charges a rate that must be assumed; break-even does not, which makes it the statistic to lead with. It is the per-side rate at which the gross edge is exactly erased: mean monthly gross return divided by traded notional.

| Signal | Annual one-way turnover | Break-even (bps/side) | Sharpe at 0 bps | at 10 bps | at 25 bps |
|---|---:|---:|---:|---:|---:|
| 12-1 Momentum | 8.87 | 10.95 | 0.143 | 0.012 | -0.183 |
| 1-Month Reversal | 19.17 | 4.33 | 0.126 | -0.167 | -0.612 |
| Low Volatility | 3.44 | -71.27 | -0.245 | -0.279 | -0.331 |
| Equal-Weight Composite | 13.35 | -3.02 | -0.054 | -0.234 | -0.506 |

These use each signal's first grid cell (for momentum, 6-month formation, decile, 5 quantiles), so they differ from the ladder's selected cell. One label correction: the docstring calls break-even round-trip, but the arithmetic and the curves make it per side, with momentum crossing zero between 10 and 15 bps and reversal between 2 and 5.

The ordering is the pre-registered prediction, break-even falling as turnover rises. Reversal turns over roughly nineteen times a year and cannot pay more than 4.33 bps per side; momentum turns over about nine times and breaks even at 10.95, approximately the rate it was charged. Negative break-evens mean low volatility and the composite have a negative gross edge that no cost assumption rescues. Since 10.95 bps is roughly where a competent desk lands, momentum is cost-marginal rather than cost-proof: the execution assumption decides it, not the signal.

### 8.1 The Corwin-Schultz estimator, and why it was not used

The intended cost model was per-name. The Corwin-Schultz (2012) estimator recovers an effective spread from daily highs and lows alone, exploiting the fact that a two-day range spans more of the true price path than two consecutive one-day ranges while the spread inflates a single day's range proportionally less. It was implemented, diagnosed and rejected before use.

Over 102,417 name-months, **71.7% of estimates are non-positive**; among the positive ones the median is 16.2 bps and the 90th percentile 47.4 bps, both implausibly wide for S&P 500 names. The pre-registration records a rank correlation of -0.10 between the estimate and realized volatility, the wrong sign: an estimator assigning tighter spreads to more volatile names is not measuring spread. It sits below its noise floor here, since a large-cap effective spread is a few basis points, smaller than the sampling error in a daily high-low range. An estimator that fails on a stated universe is a result, so the code and diagnostics are retained and the headline model is a swept flat rate with break-even.

## 9. Is there a signal?

Every test runs on the honest construction, on the momentum sleeve at the configuration chosen on training data.

**Permutation test.** The signal is shuffled across names within each date, 1,000 draws, full pipeline re-run on each. This breaks the signal-return link while leaving the market factor and the cross-sectional correlation of returns intact; permuting returns would break those too and make the null too easy to beat.

| Quantity | Value |
|---|---:|
| Observed Sharpe (gross) | 0.155 |
| Null mean | 0.013 |
| Null standard deviation | 0.266 |
| Null 95th percentile | 0.479 |
| p-value | **0.285** |
| Draws | 1,000 |

The observed Sharpe sits 0.53 null standard deviations above the null mean. It is not distinguishable from a shuffled signal.

**Bootstrap.** A stationary bootstrap with geometric block lengths (expected length by the n^(1/3) rule, 1,000 resamples) gives a 95% interval on the Sharpe of **[-0.255, 0.676]**: contains zero, 0.93 wide.

**Backtest overfitting.** CSCV over the 42 configurations gives PBO = **0.53**: the in-sample winner ranks below median out-of-sample slightly more often than not, what a pure-noise search produces. The in-sample to out-of-sample slope is **-0.431**, the wrong sign, and the winner loses money out of sample with probability 0.733.

**Deflated Sharpe.** Across 42 trials, E[max Sharpe] under the null is **0.334**, which nothing in the honest ladder reaches (L3 0.084, L4 0.167): the best number found is smaller than what the search alone would produce from noise.

**Multiple-testing haircut.** Harvey, Liu and Zhu gives t = 0.74 and a single-test p of 0.46; under Bonferroni, Holm and BHY at 42 trials the haircut Sharpe is 0.0.

**Factor attribution.** FF5 plus UMD, Newey-West errors at 5 lags, 174 months, on full-sample net returns of the training-selected configuration.

| Term | Beta | t |
|---|---:|---:|
| Mkt-RF | 0.033 | 0.48 |
| SMB | -0.109 | -0.92 |
| HML | -0.053 | -0.26 |
| RMW | -0.145 | -0.87 |
| CMA | -0.153 | -0.64 |
| **Mom (UMD)** | **1.154** | **12.16** |
| Alpha (annual) | -1.43% | **-0.43** |

R-squared is 0.627 and the information ratio -0.118: a slightly levered copy of the published momentum factor with a mildly negative intercept. The risk profile is unattractive independent of the alpha question: annualized volatility 19.9%, maximum drawdown -49.6% over a 52-month peak-to-trough, 161 of 174 months under water, skew -0.56, excess kurtosis 3.44, 5% CVaR -13.3%, hit rate 52.3%. The Daniel-Moskowitz crash regression shows the expected shape, with a bear-state up-market interaction of 0.994 at t = 2.00.

**Against the decision rule and the power bound.** The pre-registered rule required, on the holdout, net Sharpe above zero *and* a Newey-West alpha t above 2.0. Momentum clears the first (0.167) and fails the second by a wide margin, so no signal is declared surviving. Minimum detectable Sharpe here is 0.433, so a true Sharpe of 0.2 would be invisible: the null licenses neither the claim that momentum is dead nor the claim that this construction found anything.

## 10. A test that was wrong, and its correction

The first version of the permutation test charged transaction costs to both the observed strategy and each permuted draw. It reported p = 0.002 with the null centred at -0.77: a strongly significant result, from a study whose premise is that such results are usually artifacts.

It was an artifact, and the mechanism is now measured rather than argued. Permuting the signal within each date destroys its month-to-month persistence. The real signal is strongly autocorrelated, so a name in the top decile this month is likely there next month and turnover stays moderate at 7.31 annualized one-way. Permuting **roughly triples it, to 21.61**, and a Gaussian placebo, with no persistence either, lands at 21.72.

Charging costs to both sides therefore does not compare a signal against a null. It compares a low-turnover strategy against high-turnover ones and charges the difference, and nearly all of that charge lands on the null, which is why its centre collapsed to -0.77 while the observed Sharpe barely moved. The test was measuring the cost model.

Corrected to gross returns on both sides, the null recentres to 0.013 and the p-value goes to **0.285**. The recentring is the diagnostic, and it generalizes: any resampling scheme that perturbs the signal also perturbs the trading it induces, so a null not centred near zero is testing something other than the hypothesis. Costs are not ignored, they are handled by break-even in section 8.

## 11. Negative controls

All are reported gross, for the reason in section 10.

| Control | Gross Sharpe | Expected |
|---|---:|---|
| Honest signal | 0.155 | reference |
| Gaussian placebo (50 draws) | 0.030, SD 0.242 | approximately 0 |
| Staled signal (lagged 2 extra months) | 0.212 | below the honest signal |
| Leaked signal (shifted forward 1 month) | 0.175 | above the honest signal |
| Permutation null (1,000 draws) | 0.013 | 0 |

The placebo averages 0.030 over 50 draws and the permutation null centres at 0.013. Both pass. The placebo is reported as a mean and SD because a single draw carries a sampling SD of about 0.24, the same order as the permutation null, and so was not a control at all.

The staled signal, which should have lost its edge, comes in at 0.212, slightly **above** the honest signal's 0.155. Read naively this is a failed control; against the null's SD of 0.266 the gap of 0.057 is 0.21 standard deviations, which is noise. It shows the power problem from another angle: at this sample size a two-month-stale signal and a current one are indistinguishable, and that is exactly why the honest signal's own Sharpe cannot be separated from zero. The same autocorrelation weakens the leakage probe, which lifts the Sharpe only from 0.155 to 0.175; the decisive look-ahead evidence is `tests/test_no_lookahead.py`, which plants a contemporaneous-only relationship the engine must fail to exploit.

## 12. Robustness and parameter sensitivity

The momentum sleeve was re-run across the pre-registered grid (formation 6, 9, 12 months; decile, rank, inverse-vol; 5 and 10 quantiles), recording each of the 18 cells' holdout Sharpe.

| Statistic | Value |
|---|---:|
| Median holdout Sharpe | **0.091** |
| Maximum holdout Sharpe | 0.192 |
| Fraction of cells positive | 88.9% (16 of 18) |
| Max / median | 2.10 |

**The median is the headline: 0.091.** The maximum, 0.192, is an order statistic over 18 draws; reporting it would be selecting the top of a grid, the L0 shortcut this study exists to price. The ratio of 2.10 quantifies how much a naive best-cell report overstates a typical one.

The surface is well behaved: decile beats rank, which beats inverse-vol, at every formation window, and longer windows generally do better. The two negative cells are both inverse-vol at the 6-month formation (-0.006). That 88.9% share a positive sign reassures about direction, not magnitude: a median of 0.091 against a minimum detectable Sharpe of 0.433 sits inside the noise band however many cells agree. The training-selected cell is the 9-month formation, decile, 10 quantiles, whose holdout Sharpe of 0.167 is the L4 number.

## 13. Limitations, with the direction of each bias

**Delisted prices are unavailable at any free source.** 2012 coverage is 71.9%, and the missing names are disproportionately those that failed or were acquired. *Direction: the measured tax understates the true one.* The most important limitation.

**Fundamental signals are out of scope.** *Direction: unknown for the tax; the decomposition applies only to price-based signals.*

**Large-cap US only,** the tightest spreads available. *Direction: the cost rung understates these shortcuts in small caps or outside the US.*

**Borrow is not charged in the primary cost path.** *Direction: L3 and L4 net Sharpes are slightly overstated, uniformly, so orderings are unaffected.*

**Cost curves, break-evens and period effects use each signal's first grid cell.** *Direction: none systematic, but not exactly comparable to the rungs.*

**Turnover drift uses close-to-close returns even in next-open runs.** *Direction: small, and consistent across conventions by design.*

**The study is underpowered:** minimum detectable Sharpe 0.433 at 174 months. *Direction: cuts both ways. A true Sharpe of 0.2 would read as a null, and the study cannot claim no edge exists.*

**L4's delta confounds discipline with period,** per section 7. *Direction: favourable for momentum, so L4 overstates what honest reporting recovers; unfavourable for the other three, so it overstates what reporting costs.*

## 14. What I would do next

1. **Buy the delisting data.** CRSP or comparable closes the coverage gap and turns every number here from a lower bound into an estimate. Re-running the identical ladder on complete price history is the highest-value extension, and it is a purchase, not a research problem.

2. **Extend the sample backwards.** 174 months buys a minimum detectable Sharpe of 0.433; reaching 0.25 needs roughly 520 months, about 43 years.

3. **Add the fundamental sleeve** on filing-date-keyed SEC data, with the announcement lag measured rather than assumed, and test whether the sign flip generalizes to signals whose long legs hold fewer survivors.

4. **Measure the survivorship effect directly,** attributing the L0-to-L1 delta name by name, split into added survivors and removed leavers.

5. **Replace the flat cost with a real one.** TAQ effective spreads or broker fill data would work where Corwin-Schultz failed, and with momentum's break-even at 10.95 bps per side, this assumption decides the answer.

6. **Add a turnover-matched permutation null.** With permuted turnover now measured at 21.61 against the real signal's 7.31, constraining draws to match would let costs back into the test without the asymmetry that broke the first version.

---

## 15. References

Bailey, D. H., Borwein, J. M., Lopez de Prado, M., and Zhu, Q. J. (2017). "The Probability of Backtest Overfitting." *Journal of Computational Finance*, 20(4), 39-69.

Bailey, D. H., and Lopez de Prado, M. (2014). "The Deflated Sharpe Ratio." *Journal of Portfolio Management*, 40(5), 94-107.

Barroso, P., and Santa-Clara, P. (2015). "Momentum Has Its Moments." *Journal of Financial Economics*, 116(1), 111-120.

Carhart, M. M. (1997). "On Persistence in Mutual Fund Performance." *Journal of Finance*, 52(1), 57-82.

Corwin, S. A., and Schultz, P. (2012). "A Simple Way to Estimate Bid-Ask Spreads from Daily High and Low Prices." *Journal of Finance*, 67(2), 719-760.

Daniel, K., and Moskowitz, T. J. (2016). "Momentum Crashes." *Journal of Financial Economics*, 122(2), 221-247.

Fama, E. F., and French, K. R. (2015). "A Five-Factor Asset Pricing Model." *Journal of Financial Economics*, 116(1), 1-22.

Frazzini, A., and Pedersen, L. H. (2014). "Betting Against Beta." *Journal of Financial Economics*, 111(1), 1-25.

Harvey, C. R., Liu, Y., and Zhu, H. (2016). "... and the Cross-Section of Expected Returns." *Review of Financial Studies*, 29(1), 5-68.

Jegadeesh, N., and Titman, S. (1993). "Returns to Buying Winners and Selling Losers." *Journal of Finance*, 48(1), 65-91.

Newey, W. K., and West, K. D. (1987). "A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix." *Econometrica*, 55(3), 703-708.

Novy-Marx, R. (2013). "The Other Side of Value: The Gross Profitability Premium." *Journal of Financial Economics*, 108(1), 1-28.
