"""Factor attribution and risk decomposition.

An alpha without a standard error is a number, not a finding. Every regression here
uses Newey-West HAC errors, because monthly strategy returns are autocorrelated and
OLS errors would overstate significance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import cast

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats as sps

FACTOR_SETS: dict[str, list[str]] = {
    "CAPM": ["Mkt-RF"],
    "FF3": ["Mkt-RF", "SMB", "HML"],
    "Carhart4": ["Mkt-RF", "SMB", "HML", "Mom"],
    "FF5": ["Mkt-RF", "SMB", "HML", "RMW", "CMA"],
    "FF5+UMD": ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"],
}

# The crash regression estimates five coefficients, one of them off a bear-state dummy
# that is itself built from a 24-month trailing window. Under ~40 monthly observations
# the bear state is identified by a handful of months and the interaction is noise.
MIN_CRASH_OBS = 40

# Spearman's rho over fewer than three decile points is not a rank correlation.
MIN_DECILES_FOR_RHO = 3


def nw_lags(n: int) -> int:
    """Newey-West lag length by the standard rule, 4*(n/100)^(2/9)."""
    scale: float = (n / 100.0) ** (2.0 / 9.0)
    return max(math.ceil(4.0 * scale), 1)


@dataclass(frozen=True, slots=True)
class Attribution:
    """One factor regression: alpha and betas with Newey-West standard errors.

    `alpha_annual` is the monthly intercept times twelve; `info_ratio` divides that by
    the annualized residual volatility, so it is alpha per unit of the risk the factor
    model does not explain. `lags` records the HAC truncation actually used, which
    depends on the sample length and so differs between sleeves.
    """

    model: str
    alpha_monthly: float
    alpha_annual: float
    alpha_t: float
    betas: dict[str, float]
    tstats: dict[str, float]
    r_squared: float
    info_ratio: float
    n_obs: int
    lags: int


def attribute(returns: pd.Series, factors: pd.DataFrame, model: str = "FF5+UMD") -> Attribution:
    """Regress a strategy's monthly returns on a factor model with HAC errors."""
    cols = FACTOR_SETS[model]
    monthly = factors[[*cols]].resample("ME").apply(lambda x: (1.0 + x).prod() - 1.0)
    df = pd.concat([returns.rename("y"), monthly], axis=1).dropna()
    if len(df) < len(cols) + 5:
        empty = dict.fromkeys(cols, float("nan"))
        nan = float("nan")
        return Attribution(model, nan, nan, nan, empty, empty, nan, nan, len(df), 0)

    x = sm.add_constant(df[cols])
    lags = nw_lags(len(df))
    fit = sm.OLS(df["y"], x).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    resid_vol = float(np.std(fit.resid, ddof=0)) * math.sqrt(12.0)
    alpha_m = float(fit.params["const"])
    return Attribution(
        model=model,
        alpha_monthly=alpha_m,
        alpha_annual=alpha_m * 12.0,
        alpha_t=float(fit.tvalues["const"]),
        betas={c: float(fit.params[c]) for c in cols},
        tstats={c: float(fit.tvalues[c]) for c in cols},
        r_squared=float(fit.rsquared),
        info_ratio=float("nan") if resid_vol == 0 else alpha_m * 12.0 / resid_vol,
        n_obs=len(df),
        lags=lags,
    )


def crash_regression(returns: pd.Series, factors: pd.DataFrame) -> dict[str, float]:
    """Daniel-Moskowitz momentum-crash regression.

    r_t = (a0 + aB*IB) + (b0 + IB*(bB + bBU*IU))*MKT_t + e
    IB flags a bear state (negative trailing 24-month market return); IU an up month.
    `b_bu` is the option-like exposure that produces momentum crashes.
    """
    # `Series.prod` is typed as the generic scalar union; these are float returns.
    mkt = factors["Mkt-RF"].resample("ME").apply(lambda x: cast("float", (1.0 + x).prod()) - 1.0)
    df = pd.concat([returns.rename("y"), mkt.rename("mkt")], axis=1).dropna()
    if len(df) < MIN_CRASH_OBS:
        return {}
    trailing = (1.0 + df["mkt"]).rolling(24).apply(np.prod, raw=True) - 1.0
    ib = (trailing < 0).astype(float)
    iu = (df["mkt"] > 0).astype(float)
    x = pd.DataFrame(
        {
            "const": 1.0,
            "IB": ib,
            "MKT": df["mkt"],
            "IB_MKT": ib * df["mkt"],
            "IB_IU_MKT": ib * iu * df["mkt"],
        }
    )
    keep = pd.concat([df["y"], x], axis=1).dropna()
    if len(keep) < MIN_CRASH_OBS:
        return {}
    fit = sm.OLS(keep["y"], keep[x.columns]).fit(
        cov_type="HAC", cov_kwds={"maxlags": nw_lags(len(keep))}
    )
    return {
        "a0": float(fit.params["const"]),
        "a_bear": float(fit.params["IB"]),
        "b0": float(fit.params["MKT"]),
        "b_bear": float(fit.params["IB_MKT"]),
        "b_bear_up": float(fit.params["IB_IU_MKT"]),
        "t_b_bear_up": float(fit.tvalues["IB_IU_MKT"]),
        "n_obs": float(len(keep)),
    }


def decile_profile(
    z: pd.DataFrame, mask: pd.DataFrame, fwd: pd.DataFrame, n_q: int = 10
) -> pd.DataFrame:
    """Mean forward return by signal decile, raw and net of the cross-sectional mean.

    The demeaned column is the one to read. Raw decile returns in a rising market are
    positive in every decile, so a chart of them shows the market, not the signal;
    subtracting each month's equal-weighted universe return leaves the part the signal
    is actually responsible for.
    """
    valid = z.where(mask)
    ranks = valid.rank(axis=1, pct=True)
    rows: list[dict[str, float]] = []
    held = ranks.shift(1)
    # Equal-weighted return of the eligible universe in each month.
    universe_ret = fwd.where(mask).mean(axis=1)
    for q in range(n_q):
        lo, hi = q / n_q, (q + 1) / n_q
        sel = (held > lo) & (held <= hi) if q else (held >= 0) & (held <= hi)
        ret = fwd.where(sel).mean(axis=1)
        excess = ret - universe_ret
        rows.append(
            {
                "decile": q + 1,
                "mean_monthly": float(ret.mean()),
                "ann_return": float(ret.mean() * 12.0),
                "excess_ann": float(excess.mean() * 12.0),
                "n_obs": float(ret.notna().sum()),
            }
        )
    return pd.DataFrame(rows)


def spearman_monotonicity(profile: pd.DataFrame) -> float:
    """Rank correlation between decile index and realized mean return."""
    clean = profile.dropna(subset=["ann_return"])
    if len(clean) < MIN_DECILES_FOR_RHO:
        return float("nan")
    return float(sps.spearmanr(clean["decile"], clean["ann_return"]).statistic)
