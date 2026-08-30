# PRODUCT.md

## What this is
A single-page research dashboard presenting the findings of *The Survivorship Tax*:
a study measuring how much of a quantitative factor backtest's reported Sharpe ratio
is produced by methodological shortcuts rather than by signal.

## Register
Product. The design serves the data. This is a research report rendered as a web
page, not a marketing surface and not a trading terminal.

## Who reads it, where
A Texas Marketrics club officer or a quant recruiter, on a laptop, in daylight,
giving the link roughly ninety seconds before deciding whether the author knows what
they are doing. They are fluent in tearsheets. They will look for the cost
assumption, the out-of-sample split, and whether the author reports the number that
hurts.

## The job the page does
Answer one question above the fold: how much of this backtest was real? Then supply
evidence for a reader who scrolls, in the order a skeptic would ask for it.

## Non-goals
- Interactivity for its own sake. The reader scrolls; they do not explore.
- Any runtime backend. Every number is precomputed in Python and shipped as JSON.
- Persuasion. The page reports a mostly-null result and should read as such.
