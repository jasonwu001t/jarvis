# Monitoring

## Daily

```bash
python3 ~/.claude/skills/stock-evaluation/scripts/monitor.py --dir ~/AlphaResearch/research/<TICKER>
```

Refreshes price, 10-year yield, adjusted beta, the XBRL quarter list and the earnings date from
atlas, reruns the engine, writes `reports/<date>.md` and `.html` (+ `latest.html`), prints the markdown.
With atlas down the report is still written from `inputs.json` and names the failed fetches.
`--offline` skips atlas; `--apply-actuals` rolls a newly filed quarter (below).

Read it as: (1) which rule fired, (2) upside to the house target versus yesterday, (3) whether a new
quarter is flagged, (4) whether any check fails. A failing check is an input problem.

## Rules

`inputs.json → monitor.rules`: name, `when` (a Python expression over `price`, `house_target`,
`house_upside`, `bear_target`, `base_target`, `bull_target`, `price_implied_pe_base`, `pe5y_low`,
`pe5y_high`), `exposure` (target position as a fraction of full size; `null` = keep / informational)
and `action` (what the user decided in advance). Rules are evaluated in order and the first that fires
with an exposure sets the position. The META set: below bear case → 100% (price under the no-premium
value is maximum margin of safety, not a sell); add zone (≥ 20% upside) → 100%; hold zone (5-20%) →
keep; at target (−10% to 5%) → 50%; stretched (price > 10% above the house target) → 25%; multiple
above own 5-year high → informational. Rules are the user's position discipline: evaluate, report,
do not decide.

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
4. Key in the segment split from the press release (`seg:*`, `segoi:*` for the new period).
5. Replace the consensus block (unreported quarters, FY+1, FY+2) and bump `as_of.consensus_date`.
   After a Q4 print the model needs the new FY+2 year of consensus.
6. Rerun; compare with the previous report; update `tickers/<TICKER>.md` with what changed.

## Scheduling

Cron, through the repo's `bin/schedule/job` (loads the one environment file; cron has no shell
profile). The META entry: `0 7 * * 1-5 $AR/bin/schedule/job meta-monitor` → runs the skill's
`monitor.py --dir $AR/research/META`, logs to `$AR_LOG/meta-monitor.log`, posts a macOS notification
with the upside and rule, opens `reports/latest.html`. Add one case per ticker in `bin/schedule/job`
and one crontab line; `tests/test_schedule_crontab.py` pins the crontab's job count. The laptop must be
awake at the minute (cron does not run missed jobs). Installing a crontab is the owner's act.

## Staleness

The consensus block is dated; the template flags it after 100 days, and the report always shows the
date in the subtitle. Beta and the risk-free rate are live; ERP is an assumption; the forward-multiple
range should be refreshed with the consensus block.
