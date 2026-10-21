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
`pe5y_high`) and `action` (what the user decided in advance). The META set: below bear case; add
zone (≥ 20% upside); hold zone (5-20%); at target (< 5%); multiple above own 5-year high. Rules are
the user's position discipline: evaluate, report, do not decide.

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
