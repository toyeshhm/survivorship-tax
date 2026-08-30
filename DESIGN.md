# DESIGN.md

## Mood
A working paper printed on good stock. The olive of a laboratory notebook margin;
the numbers do the talking. Honesty as an aesthetic, in the register of a type
specimen showing its own workings rather than a fintech dashboard selling confidence.

## Theme decision
Light by default. This is read in daylight by someone evaluating a claim, and it is
a research report, not a trading terminal. The dark "Bloomberg terminal" treatment is
the category reflex and would signal the opposite of what the content argues. Dark
mode is implemented as a real second theme for readers who prefer it.

## Color strategy
Restrained. Neutral ground, one olive primary for structure and emphasis, and a
strictly-data palette for series encoding. Colour never decorates.

Tokens are OKLCH.

| Role | Light | Purpose |
|---|---|---|
| `--bg` | `oklch(1 0 0)` | pure white; the warmth lives in the ink, not the paper |
| `--surface` | `oklch(0.985 0.004 110)` | panels, table headers |
| `--ink` | `oklch(0.22 0.014 110)` | body text |
| `--muted` | `oklch(0.505 0.016 110)` | labels, captions; verified ≥4.5:1 on `--bg` |
| `--rule` | `oklch(0.90 0.008 110)` | hairlines |
| `--primary` | `oklch(0.50 0.088 110)` | emphasis, links, the honest series |

### Data palette (Wong, colorblind-safe)
Red/green alone is both an accessibility failure and, to this audience, a
competence tell. Series are additionally distinguished by dash pattern and direct
labels, so every chart survives grayscale.

| Token | Hex | Encodes |
|---|---|---|
| `--d-blue` | `#0072B2` | the naive, inflated result |
| `--d-vermillion` | `#D55E00` | decay, drawdown, loss |
| `--d-green` | `#009E73` | the honest result |
| `--d-orange` | `#E69F00` | third series |

## Typography
One family: a system sans stack tuned for data, plus a mono for figures.
`font-variant-numeric: tabular-nums` globally on numeric cells; every number column
right-aligned with one fixed precision per column. Misaligned decimals are the
fastest way for a financial table to lose a reader's trust.

Fixed rem scale, ratio ~1.2. No fluid clamp headings: this is product UI.

## Charts
Hand-rolled inline SVG, no charting library. The longest series is 174 monthly
points, far below the threshold where a canvas renderer earns its bundle. Writing
the SVG directly gives exact control over the axis labels, the shaded holdout
region, and the grayscale fallback, and ships nothing to parse.

## Motion
State only, 150–200ms. No page-load choreography: the reader arrived to read a
result, not to watch it assemble. Full `prefers-reduced-motion` alternative.
