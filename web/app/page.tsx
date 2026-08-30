import results from "@/public/data/results.json";
import type { Results } from "@/lib/types";
import { Waterfall } from "@/components/Waterfall";
import { EquityCurve } from "@/components/EquityCurve";
import { CostCurves } from "@/components/CostCurve";
import { DecileBars } from "@/components/DecileBars";
import { Scatter } from "@/components/Scatter";
import { Coverage } from "@/components/Coverage";
import { ThemeToggle } from "@/components/ThemeToggle";
import { f2, f3, pct1, signed, bps0 } from "@/lib/fmt";

const R = results as unknown as Results;
const KEYS = ["mom_12_1", "strev_1", "lowvol", "composite"] as const;

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div style={{ fontSize: "0.75rem", color: "var(--muted)", letterSpacing: "0.01em" }}>{label}</div>
      <div className="num" style={{ fontSize: "1.6rem", fontWeight: 600, textAlign: "left", lineHeight: 1.2 }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: "0.75rem", color: "var(--muted)" }}>{sub}</div>}
    </div>
  );
}

export default function Page() {
  const mom = R.ladders.mom_12_1!;
  const L0 = mom.rungs[0]!.sharpe;
  const L3 = mom.rungs[3]!.sharpe;
  const dUniverse = mom.rungs[1]!.delta;
  const dExec = mom.rungs[2]!.delta;
  const dCost = mom.rungs[3]!.delta;
  const drop = L0 - L3;
  const share = (d: number) => Math.round((Math.abs(d) / drop) * 100);
  const mt = R.multiple_testing;
  const perm = R.inference.permutation;
  const nc = R.negative_controls;

  return (
    <main>
      <header style={{ borderBottom: "1px solid var(--rule)", background: "var(--surface)" }}>
        <div className="wrap" style={{ paddingBlock: "clamp(2rem,5vw,3.4rem)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: "1rem" }}>
            <div>
              <h1>The Survivorship Tax</h1>
              <p className="lede" style={{ marginTop: "0.7rem" }}>
                How much of a quantitative factor backtest is signal, and how much is the
                shortcuts that produced it? This study rebuilds the same signals five times,
                removing one shortcut per rung, and reports what each was worth in Sharpe.
              </p>
            </div>
            <ThemeToggle />
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "1.6rem", marginTop: "1.6rem" }}>
            <Stat label="Sample" value={`${R.meta.n_months} months`} sub="2012-01 to 2026-06" />
            <Stat label="Universe" value="S&P 500" sub="point-in-time membership" />
            <Stat label="Configurations logged" value={String(mt.n_trials)} sub="every one reported" />
            <Stat label="Holdout" value="78 months" sub="opened once" />
          </div>
        </div>
      </header>

      <div className="wrap">
        <section>
          <h2>The finding</h2>
          <p className="lede" style={{ marginTop: "0.6rem" }}>
            On the same sample, 12-1 momentum&rsquo;s Sharpe falls from{" "}
            <strong className="num" style={{ fontSize: "1em" }}>{f3(L0)}</strong> to{" "}
            <strong className="num" style={{ fontSize: "1em" }}>{f3(L3)}</strong> as four
            standard shortcuts are removed. {Math.round((drop / L0) * 100)}% of the headline
            was method, not signal.
          </p>
          <div className="panel" style={{ marginTop: "1.4rem" }}>
            <Waterfall rungs={mom.rungs} />
          </div>
          <p className="caption">
            L0 to L3 are like-for-like: same sample, same parameters, one shortcut removed at
            a time. <strong style={{ color: "var(--ink-2)" }}>L4 is not</strong>, and the rise
            there is not an improvement. It reports the holdout alone, at the parameters
            chosen on training data, so it changes the discipline and the sample period at
            once. The period effect is separable and worth stating: the same configuration
            scores {f3(R.period_effect.mom_12_1!.train_sharpe)} on the training years and{" "}
            {f3(R.period_effect.mom_12_1!.holdout_sharpe)} on the holdout. Momentum simply had
            a better second half. The honest like-for-like number is L3.
          </p>
          <div className="grid-2" style={{ marginTop: "1.4rem" }}>
            <div>
              <h3>What each shortcut was worth</h3>
              <div className="scroll-x">
                <table style={{ marginTop: "0.6rem" }}>
                  <thead>
                    <tr>
                      <th>Shortcut removed</th>
                      <th className="n">ΔSharpe</th>
                      <th className="n">Share of drop</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Backfilled current constituents</td>
                      <td className="n">{signed(dUniverse)}</td>
                      <td className="n">{share(dUniverse)}%</td>
                    </tr>
                    <tr>
                      <td>Same-close execution</td>
                      <td className="n">{signed(dExec)}</td>
                      <td className="n">{share(dExec)}%</td>
                    </tr>
                    <tr>
                      <td>Zero transaction costs</td>
                      <td className="n">{signed(dCost)}</td>
                      <td className="n">{share(dCost)}%</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="caption">
                Universe construction alone accounts for {share(dUniverse)}% of the decay,
                more than costs and execution combined. It is also the shortcut most often
                taken silently, because pulling today&rsquo;s index members is the path of
                least resistance in every free data API.
              </p>
            </div>
            <div>
              <h3>Survivorship is not uniformly flattering</h3>
              <div className="scroll-x">
                <table style={{ marginTop: "0.6rem" }}>
                  <thead>
                    <tr>
                      <th>Signal</th>
                      <th className="n">L0 naive</th>
                      <th className="n">L1 point-in-time</th>
                      <th className="n">Δ</th>
                    </tr>
                  </thead>
                  <tbody>
                    {KEYS.map((k) => {
                      const l = R.ladders[k]!;
                      return (
                        <tr key={k}>
                          <td>{l.label}</td>
                          <td className="n">{f3(l.rungs[0]!.sharpe)}</td>
                          <td className="n">{f3(l.rungs[1]!.sharpe)}</td>
                          <td className="n" style={{
                            color: l.rungs[1]!.delta < 0 ? "var(--d-vermillion)" : "var(--d-green)",
                          }}>
                            {signed(l.rungs[1]!.delta)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <p className="caption">
                The bias has a sign, and the sign depends on the signal. Backfilling the index
                inflates momentum by {signed(-dUniverse)} but <em>deflates</em> low volatility
                by {signed(R.ladders.lowvol!.rungs[1]!.delta)}: the survivors that get added to
                the backfilled universe are disproportionately high-volatility winners, which
                is exactly what a low-volatility signal is short. &ldquo;Survivorship bias
                inflates returns&rdquo; is the wrong lesson.
              </p>
            </div>
          </div>
        </section>

        <section>
          <h2>Why the universe matters this much</h2>
          <p>
            Free price data does not merely omit a few delisted names. Of the companies that
            were genuinely in the S&P 500 in 2012, only{" "}
            <strong>{pct1(R.coverage.coverage[0] ?? 0)}</strong> can still be priced today;
            by 2026 that reaches <strong>{pct1(R.coverage.coverage[R.coverage.coverage.length - 1] ?? 0)}</strong>.
            The missing names are not random: they are the acquisitions, the bankruptcies and
            the relegations. Across the sample an average of{" "}
            <strong>{Math.round(R.coverage.mean_missing)} index members per month</strong> are
            invisible.
          </p>
          <div className="panel" style={{ marginTop: "1rem" }}>
            <Coverage dates={R.coverage.dates} coverage={R.coverage.coverage} />
          </div>
          <p className="caption">
            The upward slope is the bias. A backtest that starts in 2012 is quietly
            reconstructing the index from its survivors, and the further back it reaches the
            more selective that reconstruction becomes. Point-in-time membership fixes
            <em> who</em> is in the universe; it cannot resurrect prices that the data source
            has erased, so the measurement below is a lower bound on the true tax.
          </p>
        </section>

        <section>
          <h2>Naive against honest</h2>
          <div className="panel">
            <EquityCurve curve={R.curves.mom_12_1!} />
          </div>
          <p className="caption">
            12-1 momentum, long-short deciles. The dashed line is the naive construction; the
            solid line is the point-in-time universe with T+1 execution and costs. The shaded
            region is the pre-registered holdout, which was opened once, after parameters were
            fixed on the training period.
          </p>
        </section>

        <section>
          <h2>What survives costs</h2>
          <div className="panel">
            <CostCurves series={KEYS.map((k) => [k, R.cost_curves[k]!])} />
          </div>
          <div className="scroll-x">
            <table style={{ marginTop: "1.2rem" }}>
              <thead>
                <tr>
                  <th>Signal</th>
                  <th className="n">Turnover (×/yr)</th>
                  <th className="n">Break-even cost (bps)</th>
                  <th className="n">Net Sharpe at 10bps</th>
                </tr>
              </thead>
              <tbody>
                {KEYS.map((k) => {
                  const c = R.cost_curves[k]!;
                  const at10 = c.points.find((p) => p.bps === 10)?.sharpe ?? null;
                  return (
                    <tr key={k}>
                      <td>{c.label}</td>
                      <td className="n">{f2(c.ann_turnover)}</td>
                      <td className="n">
                        {c.break_even_bps !== null && c.break_even_bps > 0 ? bps0(c.break_even_bps) : "none"}
                      </td>
                      <td className="n">{f3(at10)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="caption">
            Break-even cost is the round-trip cost that exactly erases the gross edge, and it
            is the only cost statistic here that requires no assumption about what trading
            actually costs. Momentum breaks even at{" "}
            {bps0(R.cost_curves.mom_12_1!.break_even_bps)} bps, which is the same order as
            real large-cap costs: it is a coin flip, not a margin. One-month reversal turns
            over {f2(R.cost_curves.strev_1!.ann_turnover)}× a year and breaks even at{" "}
            {bps0(R.cost_curves.strev_1!.break_even_bps)} bps, so it is dead before it starts.
            Decay under cost is ordered by turnover, as predicted.
          </p>
          <p className="caption">
            <strong style={{ color: "var(--ink-2)" }}>A cost model that did not work.</strong>{" "}
            The Corwin-Schultz high-low spread estimator was implemented first and rejected:
            on this universe {pct1(R.cost_model.corwin_schultz.frac_non_positive)} of
            name-months return a non-positive estimate, and its cross-sectional rank
            correlation with realized volatility comes out negative. The true effective spread
            of an S&P 500 name sits below what daily high-low bars can resolve. The code and
            its diagnostics are kept in the repository, because an estimator that fails is a
            result.
          </p>
        </section>

        <section>
          <h2>Is there a signal at all?</h2>
          <p>
            The ladder measures inflation. It does not, on its own, establish that anything is
            left at the bottom. Three tests say the remainder is not distinguishable from
            noise, and one states the limit of what this sample could have detected.
          </p>
          <div className="grid-2" style={{ marginTop: "1.2rem" }}>
            <div className="panel">
              <Scatter points={mt.scatter} slope={mt.is_oos_slope} pbo={mt.pbo} />
              <p className="caption">
                Each point is one combinatorial split: the configuration that won in-sample,
                plotted against how it then did out of sample. The fitted slope is{" "}
                {f2(mt.is_oos_slope)}. Looking better in-sample predicts doing{" "}
                <em>worse</em> out of sample, which is what selecting noise looks like.
              </p>
            </div>
            <div>
              <div className="scroll-x">
                <table>
                  <thead>
                    <tr><th>Test</th><th className="n">Value</th><th>Reading</th></tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Permutation p-value</td>
                      <td className="n">{f3(perm.p_value)}</td>
                      <td>Not significant</td>
                    </tr>
                    <tr>
                      <td>Sharpe 95% CI</td>
                      <td className="n">
                        {f2(R.inference.sharpe_ci95[0])} to {f2(R.inference.sharpe_ci95[1])}
                      </td>
                      <td>Straddles zero</td>
                    </tr>
                    <tr>
                      <td>Probability of backtest overfitting</td>
                      <td className="n">{f2(mt.pbo)}</td>
                      <td>Coin flip</td>
                    </tr>
                    <tr>
                      <td>P(out-of-sample loss)</td>
                      <td className="n">{f2(mt.prob_oos_loss)}</td>
                      <td>Unfavourable</td>
                    </tr>
                    <tr>
                      <td>E[max Sharpe] under the null</td>
                      <td className="n">{f2(mt.expected_max_sharpe_null)}</td>
                      <td>Exceeds what was found</td>
                    </tr>
                    <tr>
                      <td>Minimum detectable Sharpe</td>
                      <td className="n">{f2(mt.min_detectable_sharpe)}</td>
                      <td>Study is underpowered</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="caption">
                The last row is the one that keeps the rest honest. With {R.meta.n_months}{" "}
                months, the smallest annualized Sharpe detectable at 95% confidence is{" "}
                {f2(mt.min_detectable_sharpe)}. The honest momentum estimate is well below
                that. This study therefore cannot distinguish a real Sharpe of 0.2 from zero,
                and does not claim to: the correct conclusion is <em>not proven</em>, not{" "}
                <em>disproven</em>.
              </p>
            </div>
          </div>
          <p className="caption">
            Searching {mt.n_trials} configurations, the best Sharpe one would expect from pure
            noise is {f2(mt.expected_max_sharpe_null)}. That exceeds anything found here after
            honest construction, which is the entire argument for deflating a reported Sharpe
            by the number of things that were tried.
          </p>
        </section>

        <section>
          <h2>Where the returns actually come from</h2>
          <div className="scroll-x">
            <table>
              <thead>
                <tr>
                  <th>Sleeve</th>
                  <th className="n">α (ann.)</th>
                  <th className="n">t(α)</th>
                  <th className="n">MKT</th>
                  <th className="n">SMB</th>
                  <th className="n">HML</th>
                  <th className="n">UMD</th>
                  <th className="n">R²</th>
                  <th className="n">Max DD</th>
                </tr>
              </thead>
              <tbody>
                {KEYS.map((k) => {
                  const a = R.attribution[k]!;
                  return (
                    <tr key={k}>
                      <td>{a.label}</td>
                      <td className="n">{pct1(a.alpha_annual)}</td>
                      <td className="n">{f2(a.alpha_t)}</td>
                      <td className="n">{f2(a.betas["Mkt-RF"])}</td>
                      <td className="n">{f2(a.betas.SMB)}</td>
                      <td className="n">{f2(a.betas.HML)}</td>
                      <td className="n">{f2(a.betas.Mom)}</td>
                      <td className="n">{f2(a.r_squared)}</td>
                      <td className="n">{pct1(a.metrics.max_drawdown)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="caption">
            Regressions on Fama-French 5 plus momentum, Newey-West standard errors at{" "}
            {R.attribution.mom_12_1!.lags} lags. The momentum sleeve loads{" "}
            {f2(R.attribution.mom_12_1!.betas.Mom)} on the published UMD factor with an R² of{" "}
            {f2(R.attribution.mom_12_1!.r_squared)} and an alpha of{" "}
            {pct1(R.attribution.mom_12_1!.alpha_annual)} at t ={" "}
            {f2(R.attribution.mom_12_1!.alpha_t)}. In plain terms: it is a slightly
            worse-executed copy of a factor anyone can buy, not a discovery.
          </p>
          <div style={{
            marginTop: "1.4rem", display: "grid", gap: "1.4rem",
            gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))",
          }}>
            {KEYS.map((k) => <DecileBars key={k} decile={R.deciles[k]!} />)}
          </div>
          <p className="caption">
            Decile monotonicity. A signal that works should climb from D1 to D10. Momentum
            reaches ρ = {f2(R.deciles.mom_12_1!.spearman)}, which is positive but ragged;
            low volatility comes out at ρ = {f2(R.deciles.lowvol!.spearman)}, inverted over
            this sample.
          </p>
        </section>

        <section>
          <h2>Controls and provenance</h2>
          <div className="grid-2">
            <div>
              <h3>Negative controls</h3>
              <div className="scroll-x">
                <table style={{ marginTop: "0.6rem" }}>
                  <thead><tr><th>Control</th><th className="n">Gross Sharpe</th><th>Expected</th></tr></thead>
                  <tbody>
                    <tr>
                      <td>Gaussian placebo (50 draws)</td>
                      <td className="n">{f3(nc.placebo_sharpe_gross as number)}</td>
                      <td>≈ 0 ✓</td>
                    </tr>
                    <tr>
                      <td>Permutation null mean</td>
                      <td className="n">{f3(perm.null_mean)}</td>
                      <td>≈ 0 ✓</td>
                    </tr>
                    <tr>
                      <td>Signal staled two months</td>
                      <td className="n">{f3(nc.stale_signal_sharpe_gross as number)}</td>
                      <td>Within noise</td>
                    </tr>
                    <tr>
                      <td>Honest estimate</td>
                      <td className="n">{f3(nc.honest_sharpe_gross as number)}</td>
                      <td>—</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="caption">
                The permutation null centres on {f3(perm.null_mean)} with a standard deviation
                of {f2(perm.null_sd)}; the placebo averages {f3(nc.placebo_sharpe_gross as number)}{" "}
                over {nc.placebo_n_draws as number} draws. Both sit where a correct null
                belongs. Against that spread the staled signal and the honest signal are
                indistinguishable, which is itself a finding: at this sample size the
                difference between using this month&rsquo;s momentum and a two-month-old copy
                of it is noise.
              </p>
              <h3 style={{ marginTop: "1.4rem" }}>Why the first test was wrong</h3>
              <p className="caption" style={{ marginTop: "0.4rem" }}>
                An earlier version of this permutation test charged transaction costs to both
                arms and reported p = 0.002, with the null centred at −0.77. The cause is
                measurable: permuting the signal destroys its month-to-month persistence, so
                the permuted book turns over{" "}
                <strong className="num" style={{ fontSize: "1em" }}>
                  {f2(nc.permuted_turnover_mean as number)}×
                </strong>{" "}
                a year against the real signal&rsquo;s{" "}
                <strong className="num" style={{ fontSize: "1em" }}>
                  {f2(nc.real_turnover as number)}×
                </strong>
                . Charging costs to both therefore compares a low-turnover strategy against
                high-turnover ones and bills the difference almost entirely to the null. The
                test was measuring the cost model. Run gross, the null recentres to{" "}
                {f3(perm.null_mean)} and p becomes {f3(perm.p_value)}.
              </p>
            </div>
            <div>
              <h3>How the numbers were produced</h3>
              <ul style={{ paddingLeft: "1.1rem", margin: "0.6rem 0", color: "var(--ink-2)", fontSize: "0.875rem" }}>
                <li>Signal computed from the close of month t−1; filled at the next
                    trading day&rsquo;s open, forfeiting the overnight gap.</li>
                <li>Costs charged at {R.cost_model.primary_bps_per_side} bps per side plus a{" "}
                    {R.cost_model.borrow_bps_annual} bp/yr borrow accrual on the short leg.</li>
                <li>Turnover measured against drifted pre-rebalance weights, reported one-way.</li>
                <li>No full-sample statistic anywhere in the feature path: all
                    standardization is cross-sectional, within a single date.</li>
                <li>All {mt.n_trials} configurations logged to <code>results/trials.csv</code>{" "}
                    with git SHA and config hash, whether or not they appear here.</li>
                <li>Holdout opened once, after parameter selection on training data.</li>
              </ul>
              <p className="caption" style={{ marginTop: "0.9rem" }}>
                <strong style={{ color: "var(--ink-2)" }}>Known limits, with direction.</strong>{" "}
                Delisted prices are unavailable at any price point we can reach, so the
                measured tax <em>understates</em> the true one. Fundamental signals
                (book-to-market, gross profitability) are out of scope: they need
                filing-date-accurate SEC data. Sector composition uses current
                classifications. The universe is large-cap US only, so costs here are the
                friendliest they get.
              </p>
            </div>
          </div>
        </section>
      </div>

      <footer style={{ borderTop: "1px solid var(--rule)", background: "var(--surface)", marginTop: "2rem" }}>
        <div className="wrap" style={{ paddingBlock: "1.6rem", fontSize: "0.8125rem", color: "var(--muted)" }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "1.4rem", justifyContent: "space-between" }}>
            <span>
              Generated from commit <code className="num">{R.meta.git_sha}</code> · config{" "}
              <code className="num">{R.meta.config_hash}</code> · seed{" "}
              <code className="num">{R.meta.seed}</code>
            </span>
            <span>
              <a href="https://github.com/toyeshhm/survivorship-tax">Source and full research note on GitHub</a>
            </span>
          </div>
        </div>
      </footer>
    </main>
  );
}
