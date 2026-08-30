"""Multiple-testing and significance machinery, implemented from the source papers.

References
----------
Bailey & Lopez de Prado (2012), "The Sharpe Ratio Efficient Frontier" - PSR, MinTRL.
Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio" - DSR.
Bailey, Borwein, Lopez de Prado & Zhu (2017), "The Probability of Backtest
    Overfitting" - CSCV.
Harvey & Liu (2015), "Backtesting" - the multiple-testing haircut.

"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats as sps

EULER_MASCHERONI = 0.5772156649015329

# Minimum usable sample sizes. Below these the moment estimates are meaningless
# rather than merely noisy, so the functions return NaN instead of a number.
MIN_OBS_MOMENTS = 3
MIN_TRIALS = 2


def _moments(r: np.ndarray) -> tuple[float, float, float]:
    """Per-period Sharpe, skew, and NON-excess kurtosis - the PSR convention."""
    sd = float(r.std(ddof=0))
    sr = 0.0 if sd == 0 else float(r.mean() / sd)
    skew = float(sps.skew(r, bias=False))
    kurt = float(sps.kurtosis(r, fisher=False, bias=False))
    return sr, skew, kurt


def probabilistic_sharpe(returns: pd.Series, sr_benchmark: float = 0.0) -> float:
    """P(true Sharpe > benchmark), correcting for skew, fat tails, and sample length.

    `sr_benchmark` is a PER-PERIOD Sharpe, matching the frequency of `returns`.
    """
    r = returns.dropna().to_numpy()
    n = len(r)
    if n < MIN_OBS_MOMENTS:
        return float("nan")
    sr, skew, kurt = _moments(r)
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr**2
    if denom <= 0:
        return float("nan")
    z = (sr - sr_benchmark) * np.sqrt(n - 1) / np.sqrt(denom)
    return float(sps.norm.cdf(z))


def min_track_record_length(
    returns: pd.Series, sr_benchmark: float = 0.0, alpha: float = 0.05
) -> float:
    """Periods needed for the observed Sharpe to beat the benchmark at 1-alpha."""
    r = returns.dropna().to_numpy()
    if len(r) < MIN_OBS_MOMENTS:
        return float("nan")
    sr, skew, kurt = _moments(r)
    if sr <= sr_benchmark:
        return float("inf")
    z = float(sps.norm.ppf(1.0 - alpha))
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr**2
    return float(1.0 + denom * (z / (sr - sr_benchmark)) ** 2)


def min_detectable_sharpe(n_periods: int, ppy: int = 12, alpha: float = 0.05) -> float:
    """Smallest ANNUALIZED Sharpe this sample length could detect. Reported up front.

    Inverts MinTRL under normality: a null result is only meaningful relative to
    the smallest effect the study had the power to see.
    """
    if n_periods < MIN_OBS_MOMENTS:
        return float("nan")
    z = float(sps.norm.ppf(1.0 - alpha))
    return float(z / np.sqrt(n_periods - 1) * np.sqrt(ppy))


def expected_max_sharpe(trial_sharpes: np.ndarray) -> float:
    """E[max Sharpe] under the null, given N independent-ish trials.

    The variance term is the variance ACROSS TRIAL SHARPES - not the variance of
    any one return series. Getting that wrong is the classic DSR implementation bug.
    """
    n = len(trial_sharpes)
    if n < MIN_TRIALS:
        return 0.0
    sd = float(np.std(trial_sharpes, ddof=1))
    if sd == 0:
        return 0.0
    g = EULER_MASCHERONI
    a = float(sps.norm.ppf(1.0 - 1.0 / n))
    b = float(sps.norm.ppf(1.0 - 1.0 / (n * np.e)))
    return sd * ((1.0 - g) * a + g * b)


def deflated_sharpe(returns: pd.Series, trial_sharpes: np.ndarray) -> float:
    """PSR evaluated against the Sharpe you'd expect from the best of N trials."""
    return probabilistic_sharpe(returns, expected_max_sharpe(np.asarray(trial_sharpes)))


@dataclass(frozen=True, slots=True)
class PBOResult:
    """CSCV output. `slope` < 0 across the IS/OOS scatter is the damning statistic."""

    pbo: float
    lambdas: np.ndarray
    is_sharpes: np.ndarray
    oos_sharpes: np.ndarray
    slope: float
    prob_oos_loss: float


def cscv_pbo(trial_returns: pd.DataFrame, n_blocks: int = 16) -> PBOResult:
    """Probability of backtest overfitting by combinatorially symmetric CV.

    `trial_returns` is T x N: one column per configuration tried. For every way of
    splitting the T periods into equal halves by block, take the configuration that
    won in-sample and record where it ranked out-of-sample.
    """
    mat = trial_returns.dropna(how="any")
    t, n = mat.shape
    if n < MIN_TRIALS or t < n_blocks * 2:
        empty = np.array([])
        nan = float("nan")
        return PBOResult(nan, empty, empty, empty, nan, nan)
    if n_blocks % 2:
        n_blocks -= 1
    blocks = np.array_split(np.arange(t), n_blocks)
    arr = mat.to_numpy()

    def sr(x: np.ndarray) -> np.ndarray:
        sd = x.std(axis=0, ddof=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(sd == 0, 0.0, x.mean(axis=0) / sd)

    lambdas: list[float] = []
    is_s: list[float] = []
    oos_s: list[float] = []
    for combo in itertools.combinations(range(n_blocks), n_blocks // 2):
        tr = np.concatenate([blocks[b] for b in combo])
        te = np.concatenate([blocks[b] for b in range(n_blocks) if b not in combo])
        s_is, s_oos = sr(arr[tr]), sr(arr[te])
        best = int(np.argmax(s_is))
        # Relative rank of the in-sample winner among all configs, out of sample.
        rank = float(sps.rankdata(s_oos)[best])
        omega = rank / (n + 1.0)
        omega = min(max(omega, 1e-9), 1 - 1e-9)
        lambdas.append(float(np.log(omega / (1.0 - omega))))
        is_s.append(float(s_is[best]))
        oos_s.append(float(s_oos[best]))

    lam = np.asarray(lambdas)
    isa, oosa = np.asarray(is_s), np.asarray(oos_s)
    slope = float(np.polyfit(isa, oosa, 1)[0]) if len(isa) > 1 and isa.std() > 0 else float("nan")
    return PBOResult(
        pbo=float((lam < 0).mean()),
        lambdas=lam,
        is_sharpes=isa,
        oos_sharpes=oosa,
        slope=slope,
        prob_oos_loss=float((oosa < 0).mean()),
    )


def haircut_sharpe(sr_ann: float, n_trials: int, t_periods: int, ppy: int = 12) -> dict[str, float]:
    """Harvey-Liu multiple-testing haircuts under Bonferroni, Holm, and BHY."""
    if not np.isfinite(sr_ann) or sr_ann <= 0 or t_periods < MIN_OBS_MOMENTS:
        return {k: float("nan") for k in ("t_stat", "p_single", "bonferroni", "holm", "bhy")}
    t_stat = sr_ann / np.sqrt(ppy) * np.sqrt(t_periods)
    p_single = float(2.0 * (1.0 - sps.norm.cdf(abs(t_stat))))

    def to_sr(p: float) -> float:
        p = min(max(p, 1e-16), 1 - 1e-16)
        t_adj = float(sps.norm.ppf(1.0 - p / 2.0))
        return float(t_adj / np.sqrt(t_periods) * np.sqrt(ppy))

    p_bonf = min(p_single * n_trials, 1.0)
    p_holm = min(p_single * n_trials, 1.0)  # single hypothesis: Holm == Bonferroni
    c_m = float(np.sum(1.0 / np.arange(1, n_trials + 1)))
    p_bhy = min(p_single * n_trials * c_m / 1.0, 1.0)
    return {
        "t_stat": float(t_stat),
        "p_single": p_single,
        "bonferroni": to_sr(p_bonf),
        "holm": to_sr(p_holm),
        "bhy": to_sr(p_bhy),
    }
