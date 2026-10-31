# Monitoring

## Daily

```bash
python3 ~/.claude/skills/stock-evaluation/scripts/monitor.py --dir ~/AlphaResearch/research/<TICKER>
```

Refreshes price, the 10-year yield (Treasury par curve, FRED DGS10 fallback), adjusted beta, the XBRL quarter list and the earnings date from
atlas, reruns the engine, writes `reports/<date>.md` and `.html` (+ `latest.html`), prints the markdown.
With atlas down the report is still written from `inputs.json` and names the failed fetches.
`--offline` skips atlas; `--apply-actuals` rolls a newly filed quarter (below).

Read it as: (1) which rule fired, (2) upside to the house target versus yesterday, (3) whether a new
quarter is flagged, (4) whether any check fails. A failing check is an input problem. A `## Warnings`
section (also at the top of the HTML) appears when the engine filled something in: a P/E leg turned off for a
negative or near-zero earnings base, or a cost of debt of risk-free + spread because `wacc.pretax_cost_of_debt`
is null. The ROIC and reinvestment checks name the rule they used (standard, cyclical, deferred revenue;
valuation-method.md, "Checks").

## Thesis tracker

Every monitor run also writes `reports/thesis.html` and appends `reports/history.jsonl`
(`scripts/thesis_tracker.py`). The page has four parts: the **claims board** (`thesis.claims` in
inputs.json: auto checks on the lines of the latest filed quarter, or manual status + evidence + date,
flagged Review when a due date passes), **what changed since the last run** (price, house target
split into market inputs (10-year, beta) versus model inputs, claim status changes, new quarters,
exposure), **assumption impact** (a tornado: house target at each assumption's low and high setting,
and the single-assumption break-even that puts the house target at the price) and the **history**
(target band against the price across runs). After a print, update the manual claims' evidence and
dates alongside the consensus block; the auto claims re-score themselves. AMD is the first instance.
An auto claim that misses its threshold scores Watch inside the near-miss band (`tolerance` × the threshold)
and Broken beyond it; at a zero threshold (GAAP break-even, flat q/q) the tolerance itself is the band, so
`min 0, tolerance 0.05` scores −2.3% as Watch and −8% as Broken.

Two claim kinds read beyond the model's lines: `filing_event` watches the filings index (the monitor pulls the ticker's
8-K / 8-K/A / 6-K rows with item codes from omni's `sec.submissions` through atlas; a new Item 1.01, 1.02, 3.02, 5.02…
after the claim's date flips it to Review, and the report and tracker list the material filings of the last 120 days),
and `target_vs_model` compares the base case with the company's own published targets kept in
`source/company_targets.json` (allowed as a labelled `company` source since 2026-10-25; `verified: false` marks a target
not yet restated in a filing). Since 2026-10-25 the monitor reads `sec.filing_events` (item titles, headlines, exhibit links) and falls back to the
bare `sec.submissions` index only when the events dataset has nothing for the ticker; guidance comes from
`sec.earnings_guidance` with `guidance.py` as the fallback; the fill writes `_sources` into inputs.json saying which. The monitor also reads
`/calendar/earnings/ticker/{t}/consensus-history` (the vintages of `nasdaq.earnings`: every revision of the consensus EPS
for the next report date) for the report's "EPS consensus history" line, the tracker's `consensus_revision` claim kind
and the "what changed" note when the consensus moved between runs; it is exchange-published third-party data, labelled.

## Digest (across tickers)

```bash
python3 ~/.claude/skills/stock-evaluation/scripts/digest.py --root ~/AlphaResearch/research --out ~/AlphaResearch/research/_digest/index.html
```

One page over every ticker folder, regenerated after the daily monitors (`scripts/digest.py`, nothing per
ticker). It reads each folder's `inputs.json`, the last two `reports/history.jsonl` records and the run's
`reports/<date>.md`, and renders: the **table** (price, house target, upside, rule in force, recommended
exposure, bear / base / bull, day change of price and of the house target, claims on track / watch / broken /
review, newest material filing, Nasdaq EPS consensus and its 30-day change, next earnings date, links to
`latest.html` and `thesis.html`; sorted by |upside|, or `--sort moved`), **what moved since the last run**
across tickers (house-target moves beyond 1%, rule changes, claim status changes, filings new to the
material-filings list, EPS-consensus moves for the same report date), the **exposure view** (recommended
exposure and expected-value upside per ticker; the sum of exposures as a share of a ten-slot book) and the
**claims due in the next 30 days**. A folder with no history record shows as "not run"; a folder whose
latest record is not today's is flagged in the subtitle. Same styling and Plotly CDN as the tracker.
Test: `python3 -m pytest scripts/tests/test_digest.py` from the skill root.

## Rules

`inputs.json → monitor.rules`: name, `when` (a Python expression over `price`, `house_target`,
`house_upside`, `bear_target`, `base_target`, `bull_target`, `price_implied_pe_base`, `pe5y_low`,
`pe5y_high`), `exposure` (target position as a fraction of full size; `null` = keep / informational)
and `action` (what the user decided in advance). Rules are evaluated in order and the first that fires
with an exposure sets the position. The META set: below bear case → 100% (price under the no-premium
value is maximum margin of safety, not a sell); add zone (≥ 20% upside) → 100%; hold zone (5-20%) →
keep; at target (−10% to 5%) → 50%; stretched (price > 10% above the house target) → 25%; multiple
above own 5-year high → informational. Rules are the user's position discipline: evaluate, report,
do not decide. `new_ticker.py` scaffolds the same five price rules, Stretched included (the scaffold's
`price` claim reads it).

## Position: signal, then overlays

The monitor turns the valuation into a position in two steps (`inputs.json → monitor.position_source`,
`blend.overlays`, `monitor.current_exposure`):

1. **Signal**: the expected-value exposure (reward to risk on the probability-weighted target; see
   valuation-method.md) or, if `position_source` is `rules`, the first fired rule's exposure.
2. **Overlays** (`scripts/overlays.py`, official series through atlas): a **regime gate** caps exposure at
   `cap` when Chicago Fed NFCI, VIX or the Baa spread is past its threshold; **volatility scaling**
   multiplies by `target / realised 60-day vol` (floored); a **trend filter** stages increases (at most
   `max_step_below` per decision) while the price is under its 200-day average. The report shows signal →
   after regime → after vol → recommended, next to the current position.

The reverse DCF, the realised incremental ROIC, the company's latest guidance against the consensus
block (`scripts/guidance.py`), and insider open-market flow (Forms 4) sit in the same section of the
report as context for the call.

## Backtest

```bash
python3 ~/.claude/skills/stock-evaluation/scripts/backtest.py --dir ~/AlphaResearch/research/<TICKER> --since 2023-10-01 --lag 2
```

Point in time: for every earnings release in the window (8-K item 2.02 from `sec.earnings_releases`)
the model is rebuilt as of the release plus `--lag` trading days (XBRL actuals known by then, DGS10 and
a 2-year weekly beta on that day, the close that day), the first rule that fires sets the position at
that close, and the resulting equity curve is compared with buy-and-hold and SPY (price returns, cash
at zero). Because historical sell-side consensus is not available, the forecast block is a mechanical
street: **momentum** (no look-ahead: TTM growth fading 20% a year, flat TTM margin and tax, capex on
its own TTM growth), **guidance** (the company's own next-quarter revenue range, corrected for its
historical beat against its midpoint, and full-year capex range from the 8-K exhibit, fading from
there) and **foresight** (reported figures where the forecast periods have since been reported, an
upper bound). Variants: momentum/rules, guidance/rules, guidance/EV sizing with the rate-aware multiple
and ROIC anchor, the same plus overlays, foresight/rules. Scenario assumptions, adjustments and rules
are the folder's current ones; segment adjustments become total-revenue adjustments. Outputs
`backtest/results.json`, `report.md`, `report.html` (equity curves with the exposure shading, targets
against the price path, quarter tables, honesty notes). Use it to test the rules and the method, not to
claim the analyst's historical track record; one name and one window prove nothing.

## After an earnings print

1. Run the monitor: a filed quarter the model does not yet carry shows as "reported quarters since
   the consensus block" with actual versus the consensus the model carried (revenue, operating income,
   pretax, tax, net income, EPS, shares, D&A, SBC, OCF, capex, dividends, buybacks, cash, debt, equity).
2. Judge the thesis lines first: did the adjusted line (ads, capex, …) beat consensus by the pp the
   house assumed? Did guidance move the FY+1 consensus?
3. `--apply-actuals` writes the quarter into `inputs.json` (cash + marketable securities, debt +
   finance leases carried from the last 10-K, investments, other income) and rolls `as_of`.
4. Key in the segment split from the press release (`seg:*`, `segoi:*` for the new period), or rerun
   `fill_from_atlas.py` once atlas has the segment facts.
5. Replace the consensus block (unreported quarters, FY+1, FY+2) and bump `as_of.consensus_date`.
   After a Q4 print the model needs the new FY+2 year of consensus: rerun `fill_from_atlas.py`, which keeps
   the reported year as filed (listed once), builds FY+1 from the Q1 guide (beat-adjusted) and the prior
   year's quarters, and FY+2 from FY+1.
6. Rerun; compare with the previous report; update `tickers/<TICKER>.md` with what changed.

## Scheduling

Cron, through the repo's `bin/schedule/job` (loads the one environment file; cron has no shell
profile). The META entry: `0 7 * * 1-5 $AR/bin/schedule/job meta-monitor` → runs the skill's
`monitor.py --dir $AR/research/META`, logs to `$AR_LOG/meta-monitor.log`, posts a macOS notification
with the upside and rule, opens `reports/latest.html`. Any other ticker uses the generic
`job ticker-monitor <TICKER>` case (AMD: `5 7 * * 1-5 $AR/bin/schedule/job ticker-monitor AMD`, which
opens `reports/thesis.html`): one crontab line per ticker; `tests/test_schedule_crontab.py` pins the crontab's job count. The laptop must be
awake at the minute (cron does not run missed jobs). Installing a crontab is the owner's act.

The digest runs once after the ticker monitors, from one more crontab line:

```
10 7 * * 1-5 $AR/bin/schedule/job digest
```

`bin/schedule/job` needs a `digest` case for it (the owner's repo; the skill does not edit it). Shaped like
`ticker-monitor`, it would run `$PY $SKILL/scripts/digest.py --root $AR/research --out $AR/research/_digest/index.html`
with `date -u` first, appending to `$AR_LOG/digest.log`, then `open $AR/research/_digest/index.html`; its exit
code is digest.py's, so cron mails a failed run. 07:10 leaves five minutes after the last ticker monitor; a
ticker whose monitor has not finished shows its previous run's record and the subtitle names it as not run
today. `tests/test_schedule_crontab.py` pins the job count: the new line changes it.

## Staleness

The consensus block is dated; the template flags it after 100 days, and the report always shows the
date in the subtitle. Beta and the risk-free rate are live, and the thesis tracker shows their dates and flags them when stale; ERP is an assumption; the forward-multiple
range should be refreshed with the consensus block.
