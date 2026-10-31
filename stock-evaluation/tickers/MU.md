# MU — Micron Technology, Inc. playbook

## Status

- Live folder: `~/AlphaResearch/research/MU/` (`inputs.json`, `narrative.py`, `source/street_and_gap_patch.py`, `source/exhibits/`,
  `reports/`). Fiscal year ends the Thursday closest to August 31 (FY2026 ended 2026-09-03, FY2027 ends 2027-09-02;
  `fiscal_year_end_month` 9 so the engine's FY end sits after the balance-sheet date). Latest reported: Q4 FY2026 (10-K).
  Next print: Q1 FY2027 on 2026-12-16 (Nasdaq EPS consensus $37.93).
- Built 2026-10-25 through the **generic path** (`new_ticker.py --fye 8` → `fill_from_atlas.py --since-fy 2023` →
  `source/street_and_gap_patch.py` → `monitor.py`), the second onboarding after AVGO and the first with a 10-K as the latest
  filing. 美投 covers MU (5+2 of 2026-10-07, view 2026-10-18: 积极, risk 4 (their highest), target $1,447 = 7x FY2028 EPS of
  ~$207, "not suitable for buy-and-hold or buy-the-dip"); the house view is built from Micron's own filings with 美投 as the
  external frame. Scheduled: none. Position: none recorded.

## Method and the street

Template method (three-scenario DCF + P/E on quarters-5-8 **GAAP** EPS, 50/50, rate-aware multiple, ROIC anchor, overlays) with
two departures, both in `blend`: `convergence_years` **6** (a memory cycle normalises margins within one cycle; a 12-year
glide from an 80% margin would hold the peak for a decade) and GAAP earnings (Micron's non-GAAP adds back SBC only, ~1% of
revenue). With Q4 the latest quarter there are no forecast quarters: the explicit period is FY2027 and FY2028 and the P/E
leg is FY2028 EPS alone.

- **No sell-side consensus.** The street is written by `source/street_and_gap_patch.py` from the 8-K of 2026-09-30: Q1 FY2027
  guide $61.5bn ± $1.5bn x 1.088 (median beat of the last six guides) = $66.9bn, then q/q +5% / +3% / +2% → FY2027 $283bn
  (+113%) at an 82% GAAP operating margin (the guide implies 82.2% for Q1: 85.95% gross margin, $2.31bn opex); FY2028 +4% at
  76%; tax 15%; other income $2.0bn/yr (interest on $73bn of cash and investments); capex $55bn/yr (FY2026 $30.7bn and
  "increasing", no FY2027 figure in the 8-K); shares 1,150m flat; DPS $0.60. FY2028 GAAP EPS $167 (美投 ~$207 with DRAM prices
  held high and buybacks from December).
- Scenarios (judgement 2026-10-25): bear revenue −10pp FY2027 / −30pp FY2028, margin −6pp / −20pp (a 2027 top), steady 20%
  margin / 14% ROIC, 5x; base = the street, 30% / 16%, 7x (美投's multiple); bull +6pp / +15pp, +2pp / +5pp, 38% / 22%, 10x.
  Probabilities 30/45/25. Steady ROIC sits at or above the 13.4% WACC a 2.0 beta produces because the engine's check demands
  it; Micron's through-cycle ROIC is lower, and the bear margin carries that.
- Reference multiples 5x / 12x / 30x: own approximate five-year forward P/E range (low at peaks, high at troughs), not official.

First run (2026-10-25, price $877.55, beta 2.01 adjusted (raw 2.51), 10-year 5.00%, WACC 13.4%): bear / base / bull
**393 / 1,072 / 1,877**, house 1,072 (+22%, rule "Add zone", expected value 1,070, exposure 60% signal → **39%** after the
volatility overlay: realised 60-day vol 54% against the 35% target); reverse DCF: the price needs −9.8pp a year on the
street or a 23% steady margin. Price pays 5.3x base FY2028 EPS. Read it as: the market already pays a trough multiple for
peak earnings; the upside is the contracts holding the margin through 2028, the downside is every memory top in history.

## Thesis and what moves it

Memory is the data-centre bottleneck; FY2026 revenue $133bn (+256%) at a 75% GAAP margin, Q4 $54.2bn (+379% y/y, +31% q/q)
at 86.8% gross margin, Q1 guide +13% q/q. New this cycle: Strategic Customer Agreements with floor prices took RPO from $5bn
to **$134bn** in one quarter and brought $12.7bn of customer deposits (financing cash flow); HBM takes three times the wafers
per bit, so effective supply growth stays below demand. Risks: the top is unpredictable (EPS fell 80-90% in past downturns,
the stock halves before the filings show it), capacity landing together in 2027-28 (Micron's own $55bn/yr, Samsung, SK
Hynix, CXMT), HBM yield and qualification (smallest share of the three), AI demand disappointing. Proven wrong by the first
sequential revenue decline, inventory days rising two quarters running, a Q2 guide below Q1, or capex guided above 30% of
revenue: 美投's rule for cyclicals is to exit when supply loosens, not when earnings fall.

## Company-specific data

- Segments: four business units since FY2025 (`sec.segment_facts` members CMBU Cloud Memory, CDBU Core Data Center, MCBU
  Mobile and Client, AEBU Automotive and Embedded, plus "Other Operating Segment"; the older CNBU/EBU/MBU/SBU members stop at
  FY2024). Q4 FY2026 and the FY2026 annual were keyed from the press-release business-unit table (revenue, operating margin x
  revenue) because the FY2026 10-K is not in the FS&N data set yet; the patch overwrites them, delete that block when XBRL lands.
- XBRL quirks (all patched, every one a WARNING in `_sources.notes`): Q4 share counts never served (any year) and the FY2026
  annual diluted count missing; `total_debt` blank Q2-Q3 FY2026 (Micron tags `LongTermDebtAndCapitalLeaseObligations` +
  `DebtCurrent`, the chain wants `LongTermDebt`); cash composite misses `AvailableForSaleSecuritiesDebtSecuritiesCurrent`
  ($5.1bn) and `...Noncurrent` ($30.0bn, now in `investments`); `rpo` served but not carried into a line (keyed); interest
  expense $106m FY2026 is net of capitalised interest, so the cost of debt is set (5%), not derived.
- Guidance wording: a table "Business Outlook … FQ1-27 … Revenue $61.5 billion ± $1.5 billion / Gross margin Approximately
  85.95% / Operating expenses Approximately $2.31 billion / Diluted earnings per share $37.84 ± $1.00", GAAP and non-GAAP
  columns. Neither `sec.earnings_guidance` (0 rows for MU) nor `guidance.py` reads the ± form; the Q4 FY2025 release and
  earlier use "± $200 million". Beat history vs the midpoint: 1.058, 1.057, 1.091, 1.276, 1.238, 1.085 (median 1.088).
- Non-GAAP: SBC, patent licence charges ($500m in Q4 FY2026), debt prepayment losses; `sec.earnings_non_gaap` has 0 rows for
  MU although every release carries the reconciliation ("GAAP gross margin / Stock-based compensation / Non-GAAP gross margin").
- Filings worth re-reading: 8-K 2026-08-26 (Bhatia President and COO, 5.02), 8-K 2026-03-25/31 (cash tender offers, debt
  retired), 8-K 2024-12-09 (CHIPS direct funding agreements, Idaho and New York), 8-K 2023-05-21 (CAC conclusion, China).
  `sec.filing_events` has 76 rows for MU (already collected by the cron universe; the hand `omni sync` added nothing).
- Customer deposits sit in financing cash flow ($12.7bn FY2026), so OCF and the derived working capital exclude them.

## What to watch at each print (Q1 FY2027, 2026-12-16)

1. Revenue against $61.5bn ± $1.5bn and the street's $66.9bn; q/q growth positive (`rev_qoq` is the tripwire).
2. Gross margin against ~86% (claim floor 80%); operating margin against ~82% (floor 75%).
3. Core Data Center and Cloud Memory sequential growth and margins; HBM commentary (share, 1-gamma, HBM4 qualification).
4. RPO and customer contract liabilities (claim floor $100bn): are the agreements growing or being drawn down?
5. Capex guide for FY2027 against the $55bn carried; inventory days and receivables; buyback authorisation after December.

## Findings: where the generic path fell short (2026-10-25)

Everything below was needed to get from `fill_from_atlas.py`'s output to a model that runs; "raw" the fill produced a
momentum street of +256% a year (FY2027 $406bn, FY2028 $1.07tn), listed FY2026 twice, had no Q4 share count (market cap 0)
and a null cost of debt (monitor crash).

**atlas KPI chains / `research/fundamentals`**
1. Q4 share counts (`shares_diluted`, `eps_diluted`, `dividends_per_share`) are never served (20234, 20244, 20254, 20264): the
   Q4 derivation covers flows only. The FY2026 annual `shares_diluted` is missing too although the 10-K tags 1,143m. Fix:
   derive Q4 averages from the 10-K (annual x4 − YTD x3) or serve the 10-K's own Q4 figure; serve the annual.
2. `total_debt` blank for Q2-Q3 FY2026: Micron tags `LongTermDebt` only in the 10-K and Q1, `LongTermDebtAndCapitalLeaseObligations`
   + `DebtCurrent` every quarter (AVGO finding 3 again). Fix: add both to the chain / composite.
3. The cash composite looks for `MarketableSecuritiesCurrent`; Micron tags `AvailableForSaleSecuritiesDebtSecuritiesCurrent`
   ($5.1bn) and `...Noncurrent` ($30.0bn). Fix: AFS tags in the cash chain; a `long_term_investments` KPI for the noncurrent one.
4. `interest_expense` is net of capitalised interest (FY2026 $106m on $5-14bn of debt): TTM interest / debt is not a cost of
   debt. Fix: the fill floors the derived rate with a coupon source (FRED Baa) and says which it used.
5. `rpo` ($134bn, `RevenueRemainingPerformanceObligation`) is served and not carried (AVGO 13). Keyed as a line here so the
   `ltas` claim can run a `level` check.
6. `sec.segment_facts` lags the FS&N data set: the FY2026 10-K (filed 2026-10) has no rows, so Q4 and FY2026 segments were blank
   and the fill built no segment forecast (it needs four quarters). Fix: ingest segment facts from the filer's own XBRL
   instance when FS&N lags, or fall back to the press-release table with a WARNING.
7. Segment members are XBRL codes (CMBU, CDBU, MCBU, AEBU). Fix: carry the member's label from the taxonomy.

**`fill_from_atlas.py` / `new_ticker.py`**
8. A Q4-latest fill lists the fiscal year twice (actual and "consensus"), rebuilds its lines as a street year (net income
   $84,628m vs $84,969m filed), creates no next-quarter period and takes the momentum growth from the year just closed
   (+256%). Fix: when `latest_reported_q == 4`, keep the FY actual and forecast FY+1 (quarters or annual) and FY+2 from the
   Q1 guide.
9. Neither `sec.earnings_guidance` nor `guidance.py` reads "Revenue $61.5 billion ± $1.5 billion" (table rows under "Business
   Outlook", label "FQ1-27"), nor "Gross margin Approximately 85.95%" / "Operating expenses Approximately $2.31 billion" / "Diluted
   earnings per share $37.84 ± $1.00". Fix: a ± range rule, the FQn-YY label, and margin / opex / EPS rows.
10. Without parsed guides there is no beat history: keyed from the cached exhibits (median 1.088 over six).
11. `pretax_cost_of_debt` null → `TypeError` in `wacc()` (AVGO 7 again).
12. Forecast `other_income` 0 (AVGO 8): $1.1bn of interest income in FY2026, $2bn/yr carried here.
13. `fiscal_year_end_month` cannot place a 52/53-week year that ends on 2026-09-03: month 8 puts the engine's FY end before the
    balance-sheet date. Used 9. Fix: an exact FY-end date derived from the 10-K period end (AVGO 24).
14. The fill's `_street` has no field for a hand-keyed guide; the patch overwrites the dict and `as_of.consensus_source`.

**omni datasets**
15. `sec.earnings_non_gaap`: 0 rows for MU across 19 releases with full reconciliation tables (AVGO 19 again; Micron's labels:
    "GAAP gross margin", "Stock-based compensation", "Patent license charges", "Loss on debt prepayments", "Estimated tax
    effects of above and other tax adjustments").
16. `sec.filing_events` and `sec.earnings_releases` were already current for MU (cron universe `sp500`); the hand `omni sync`
    added nothing: the add-time gap (AVGO 20) is only for names outside the S&P 500.

**skill (report, engine, monitor, tracker)**
17. `report_html.ROW_SPECS` and the engine's `yoy:` rows still hard-code META's segments (AVGO 22): the four business units
    appear only in the narrative.
18. The check "Steady-state ROIC at or above WACC (all scenarios)" fails for any bear scenario whose ROIC sits below a 13%
    WACC; for a cyclical that is the bear case by design. Fix: warn, don't fail, or compare against the scenario's own cost of
    capital. The "implied return on new investment ≥ WACC in every transition year" warning fires on every fading cyclical
    (ΔNOPAT < 0 while reinvesting): skip years where margin is gliding down.
19. The volatility overlay (target 35%, floor 0.25) cuts MU to 39% from a 60% signal: right for a 54%-vol name, but the report
    should say the overlay, not the valuation, set the position.
20. The tracker's `qoq` kind scores the latest filed quarter only; for a cyclical the two-quarter trend (inventory days) needs a
    `trend` kind or a `periods: 2` option.
21. Monitor footer still says segments are manual (AVGO 23).

**Hand-keyed in this folder**: everything in `source/street_and_gap_patch.py` (findings 1-3, 5, 6, 8-12 and the whole street),
the scenario anchors, the reference multiples, `convergence_years` 6, the evidence of the `q1_guide`, `buyback`,
`cycle_top`, `supply_2028`, `hbm_execution` and `china` claims. From atlas with no fallback: the fundamentals route (every
flow line, FY2023-26), segment facts through Q3 FY2026, filing events (76 rows), the consensus history, the price, beta inputs.

## Log

- 2026-10-25: onboarded through the generic path (MU added to atlas list LST-33DD8C7D, collected at once as an S&P 500 name).
  Fill, then `street_and_gap_patch.py` (Q4-latest fixes, Q4 segments from the release, guidance street). House view
  Positive / 积极, cycle risk 4: 393 / 1,072 / 1,877 at $877.55, rule Add zone, exposure 39% after the vol overlay; 17 claims
  (11 on track, 4 watch, 2 pending). Findings list written for the pipeline plan.
- 2026-10-25: skill faults fixed (findings 8, 11, 12, 17, 18): a Q4-latest refill now lists FY2026 once, keeps it as filed and starts the street at FY2027 Q1 (the guided quarter once the ± form parses; until then momentum capped at ±50%: a scratch refill gave FY2027 $200bn against this patch's guide-based $283bn, so keep the patch's street) and forecasts other income from InvestmentIncomeNet ($1.85bn a year, the patch keys $2.0bn). Checks use the cyclical rule (detected: FY2023 revenue -49%): probability-weighted steady ROIC and through-cycle realised ROIC pass; the transition-return check still warns (9.5% at the 30% mid-cycle margin against a 13.4% WACC: the FY2028 capex intensity, not the margin fade). Monitor rerun: 393 / 1,072 / 1,877 unchanged.
