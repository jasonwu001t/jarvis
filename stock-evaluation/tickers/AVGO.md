# AVGO — Broadcom Inc. playbook

## Status

- Live folder: `~/AlphaResearch/research/AVGO/` (`inputs.json`, `narrative.py`, `source/xbrl_gap_patch.py`, `source/exhibits/`,
  `reports/`). Fiscal year ends the Sunday nearest October 31 (FY2025 ended 2025-11-02, FY2026 ends 2026-11-01;
  `fiscal_year_end_month` 10). Latest reported Q3 FY2026 (quarter ended 2026-08-02). Next print: Q4 FY2026 on 2026-12-10.
- Built 2026-10-25 through the **generic path** (`new_ticker.py` → `fill_from_atlas.py --since-fy 2023 --fade 0.6` →
  `source/xbrl_gap_patch.py` → `monitor.py`) as the onboarding test of the 2026-10-25 pipeline lanes. 美投 covers AVGO
  (5+2 of 2026-10-05, 非常积极, risk 2, target $475 = 25x FY2027 non-GAAP EPS of $19); the house view here is built from
  Broadcom's own filings with 美投 as the external frame. Scheduled: none. Position: none recorded.

## Method and the street

Template method (three-scenario DCF with 12-year convergence + P/E on quarters-5-8 **adjusted** EPS, 50/50, rate-aware
multiple, ROIC anchor, overlays). `earnings_basis "adjusted"`: adjustments = amortisation of acquired intangibles after
tax (AMD convention; SBC stays a cost), so adjusted EPS sits ~10% under Broadcom's non-GAAP EPS.

- **No sell-side consensus.** The street is the fill's guidance street: Q4 FY2026 at the company's $34.8bn guide
  (8-K 2026-09-02, beat-adjusted x1.013 over six releases), then the guide's +96% y/y faded 60% a year: FY2027 $167bn
  (+57%; 美投 +56%), FY2028 $225bn (+34%). FY2026's GAAP operating margin (49%) carried forward; tax 10% (TTM, clamped);
  net interest −$2.7bn/yr carried; capex 1.5% of revenue; amortisation from the 10-Q schedule ($7.0bn FY2027, $5.8bn FY2028).
- Scenarios (judgement 2026-10-25): bear growth −15pp, margin −4pp, steady 38% / ROIC 18%, 20x; base = the street, 45% / 25%,
  28x (美投's 25x on non-GAAP ≈ 28x on this basis); bull +10pp, +3pp, 50% / 30%, 34x. Probabilities 25/50/25.
- Reference multiples 16x / 27x / 42x: own approximate five-year forward range on the adjusted basis, not official.

First run (2026-10-25, price $321.68, beta 1.86 adjusted (raw 2.29), 10-year 5.00%, WACC 12.5%): bear / base / bull
**259 / 572 / 956**, house 572 (+78%, rule "Add zone", expected value 590, exposure 93% after the vol overlay); reverse DCF:
the price needs −18pp a year on the street or a 17% steady margin. Price pays 16.4x base quarters-5-8 adjusted EPS ($19.63).
Read it as: the booked ramp (RPO $179bn) is not in the price unless the four customers fail to take delivery; the engine's
12-year glide from +34% is generous, as for every hyper-growth name (see the sensitivity grids).

## Thesis and what moves it

Broadcom designs the custom AI accelerators of Google, Meta, OpenAI and Anthropic and the Ethernet networking around them
(美投: the biggest beneficiary of AI cost-down; competition fears from MediaTek/Marvell overdone), with VMware, CA and
Symantec as a profit ballast (42% of FY2025 revenue, 49% of operating profit). AI semiconductor revenue $16.7bn in Q3 FY2026
(+221%), guided $21.7bn in Q4; RPO $179bn (from $33bn at FY2025 end); Q4 guide $34.8bn (+93%) at 66% non-GAAP operating
margin. Risks: customer concentration (two of the four are private labs), ASIC competition and Nvidia's cadence, AI capex
timing, VMware churn, $59bn of debt. Proven wrong by a top-customer programme re-sourced (8-K 1.02, or an 8.01 agreement
with a competitor), AI revenue below the guide, or semiconductor segment margin under 55%.

## Company-specific data

- Segments from `sec.segment_facts` (members Semiconductor Solutions, Infrastructure Software; "Unallocated Expenses" is
  OI-only and skipped). Segment OI excludes amortisation, SBC and restructuring, so segment margins (61% / 84%) sit far above
  GAAP (54%). The AI semiconductor revenue line is press-release prose only (keyed into the `ai_revenue` claim each quarter).
- XBRL quirks (all patched by `source/xbrl_gap_patch.py`, every one a WARNING in `_sources.notes`): net income tagged
  `ProfitLoss`; equity `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest`; debt
  `LongTermDebtAndCapitalLeaseObligations` + `LongTermDebtCurrent`; 10-for-1 split 2024-07-15; FY2023-24 10-Qs tag no
  us-gaap amortisation (custom element) so those quarters' D&A are prorated from the annual; Q4 FY2025 carried a $1.65bn
  tax benefit (TTM tax 5%; the street clamps to 10%, scenarios use 14%).
- Guidance wording: "Fourth quarter fiscal year 2026 revenue guidance of approximately $34.8 billion" (parses) and
  "Non-GAAP operating income guidance of approximately 66 percent of projected revenue" (does not). FY2024 releases guided
  the fiscal year ("Fiscal year 2024 revenue guidance of approximately $51.0 billion"), FY2023 and earlier the quarter with
  Adjusted EBITDA as a percent of revenue.
- Filings worth re-reading: Google long-term agreement (8-K 2026-04-06, Item 8.01), Apple agreement through 2031
  (2026-07-06, 8.01), CFO transition Spears → Thuener (2026-04-02, 5.02), the VMware financing 8-Ks (2.03), the Q3 10-Q's
  RPO and concentration notes.
- Insider flow: programme sales ($534m over three months); informational.

## What to watch at each print

1. AI semiconductor revenue vs the guide ($21.7bn for Q4 FY2026) and the next guide; RPO direction.
2. Semiconductor Solutions growth (+127% in Q3) and segment margin (61%, floor 55%); gross margin (69%, floor 62%).
3. Q1 FY2027 revenue guide vs the model's FY2027 path ($167bn, +57%); non-GAAP operating margin guide (66%).
4. Infrastructure Software growth (+29%) and margin (84%): VMware conversion vs churn.
5. Receivables (+$6.5bn YTD) and OCF/revenue (48%, floor 40%); debt paydown; any 1.01/1.02/2.01/3.02 or an 8.01 naming a customer.
6. After the print: `fill_from_atlas.py --since-fy 2023 --fade 0.6`, then `source/xbrl_gap_patch.py`, re-key the
   `ai_revenue` / `q4_guide` / `backlog` evidence, rerun.

## Findings: where the generic path fell short (2026-10-25)

Everything below was needed to get from `fill_from_atlas.py`'s output to a model that runs; the fix each needs is for the
pipeline plan. "Raw" = the fill with no patch: the monitor crashed on `pretax_cost_of_debt = None`, and with that set it
would have run with no net income after FY2024, zero equity, debt only from FY2025 Q4 and pre-split share counts.

**atlas KPI chains (`atlas/company_types.py`, `xbrl.py`)**
1. `net_income` = `[NetIncomeLoss]` serves AVGO only FY2022-24 annuals. Broadcom tags `ProfitLoss` on every quarter and year
   and `NetIncomeLossAvailableToCommonStockholdersBasic` to FY2024. Fix: chain `NetIncomeLoss | ProfitLoss |
   NetIncomeLossAvailableToCommonStockholdersBasic` (ProfitLoss includes NCI; subtract `NetIncomeLossAttributableToNoncontrollingInterest` when tagged).
2. `equity` = `[StockholdersEquity]` serves nothing after 2019. Fix: add `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest`.
3. `total_debt` = `LongTermDebtNoncurrent` exists only from FY2025 Q4; Broadcom's constant tag is
   `LongTermDebtAndCapitalLeaseObligations` (noncurrent, incl. finance leases) with `LongTermDebtCurrent` / `DebtCurrent`
   for the current portion and `DebtLongtermAndShorttermCombinedAmount` at some dates. Fix: add the first to the `total_debt`
   chain and a composite `LongTermDebtAndCapitalLeaseObligations + LongTermDebtCurrent` to `long_term_debt_incl_current`.
4. Share splits: the 10-for-1 split of 2024-07-15 is in the facts (`StockholdersEquityNoteStockSplitConversionRatio1` = 10
   at 2024-07-12) but `/research/fundamentals` serves pre-split quarters as filed (429m diluted shares, $4.10 DPS) next to
   restated annuals (freshest filing wins). Fix: apply the split-ratio fact (or `alpaca.corporate_actions` splits) to
   per-share and share-count KPIs before the split date.
5. D&A for FY2023-24 quarters: the 10-Qs tag `Depreciation` (YTD) and no us-gaap amortisation (the cash-flow line is a
   company extension), so the composite is withheld and the quarters are blank; the fill's 2-year realised ROIC then reads
   those blanks as zero. Fix: a chain leg from the issuer extension taxonomy when its standard label matches, or the FS&N
   data (which carries extension elements) as the source; failing that, prorate the annual and flag it.
6. `depreciation_amortization` is served as `Depreciation+AmortizationOfIntangibleAssets` from FY2025 Q1: correct.

**`fill_from_atlas.py` / `new_ticker.py`**
7. `wacc.pretax_cost_of_debt` stays `null` → `monitor.py` raises `TypeError` in `wacc()`. Fix: the fill derives it
   (TTM `interest_expense` / average debt; annualise when the Q4 interest row is missing, as here: 4.92%).
8. Forecast `other_income` is 0, so pretax = operating income: for an issuer with $59bn of debt that overstates net income
   by ~$2.4bn a year. Fix: carry TTM other income (or interest at the debt path) into the street.
9. The fade: 80% a year off a +96% guided quarter gives FY2027 +77% and FY2028 +61%; used `--fade 0.6` (+57% / +34%).
   Fix: tie the fade to the growth level (or to RPO cover), or cap the street's FY+1 growth and say so.
10. The guided quarter's margin is the TTM margin (48%) although the latest quarter was 54% and the guide says 66%
    non-GAAP; the operating-income guide did not parse (16). Fix: parse (16); fall back to the latest quarter's margin.
11. Segment forecasts do not sum to the guided total in the guided quarter (35,762 vs 35,252). Fix: scale to the total.
12. `wc_increase` = NOPAT + D&A + SBC − OCF absorbs after-tax interest paid (~$2bn/yr: OCF is after interest), so FCFF is
    understated by ~3% and interest is counted twice (WACC). Fix: add back after-tax `interest_expense` in the derivation.
13. The `rpo` KPI atlas serves ($179bn, `RevenueRemainingPerformanceObligation`) is not carried into a line; the backlog
    claim is manual. Fix: `KPI_TO_LINE` gains `rpo`, the tracker can then run a `level` / `qoq` claim on it.
14. `--since-fy` history includes FY2022 quarters, where the split problem (4) also shows.

**`sec.earnings_guidance` (omni `_sec_guidance.py`) and `atlas_data.guidance_releases`**
15. Revenue guides parse only from the 2024-09 release. FY2024 releases guided the fiscal year ("Fiscal year 2024 revenue
    guidance of approximately $51.0 billion"): metric revenue, period_kind fiscal_year, which `atlas_data` maps to nothing.
    Fix: a `revenue_full_year` name the fill can use when no quarter is guided.
16. "Non-GAAP operating income guidance of approximately 66 percent of projected revenue" (and FY2023-24's "Adjusted EBITDA
    guidance of approximately 61 percent of projected revenue") give no row: a percentage after a dollar metric is rejected
    by design. Fix: a rule mapping "<metric> ... N percent of (projected) revenue" to the matching margin metric.
17. FY2023 and earlier outlook bullets ("First quarter revenue guidance of approximately $8.9 billion") name no year; the
    2026 releases produce the same bullet as a row with `fiscal_year` null beside the dated headline row, and `atlas_data`
    drops null-year rows. Fix: take the year from the "First Quarter Fiscal Year 2023 Business Outlook" heading (a bullet
    inside the section), or infer it from the release date in `atlas_data`.
18. Product-line guidance ("we expect AI semiconductor revenue to accelerate to $21.7 billion") is dropped by design
    (capitalised name before the noun). For AVGO this is the thesis KPI. Fix: an opt-in product-line column, or at least
    keep the sentence in a `dropped_sentences` sidecar the skill can show.
19. `sec.earnings_non_gaap`: 0 rows across 18 releases although every release carries a full GAAP-to-non-GAAP
    reconciliation table. Fix: check `NON_GAAP_RULES` against Broadcom's labels ("Amortization of acquisition-related
    intangible assets", "Stock-based compensation expense", "Restructuring and other charges", "Acquisition-related costs").

**atlas lists and `sec.filing_events`**
20. Adding a ticker queues four SEC datasets (`lists.py SEC_DATASETS`); `sec.filing_events`, `sec.earnings_guidance`,
    `sec.earnings_non_gaap` and the press-release figures arrive with the next cron run. Here they were synced by hand
    (`omni sync <dataset> -p ticker=AVGO`: 107 event rows / 86 filings, 35 guidance rows). Fix: add them to the add-time jobs.
21. Broadcom files its customer agreements under Item 8.01 (Google long-term agreement 2026-04-06, Apple 2026-07-06), so a
    1.01/1.02 watch misses the thesis events, and 8.01 is noisy (68 of 107 rows: dividends, debt pricing). Fix: a
    `headline` regex option on `filing_event` claims so 8.01 rows can be watched selectively.

**skill (report, engine, monitor)**
22. `report_html.ROW_SPECS` and the engine's `yoy:` rows hard-code META's segment names: AVGO's segments do not appear in
    the income-statement table and `yoy:seg:*` is not computed (the narrative computes its own). Fix: build the segment rows
    from `inputs["segments"]`.
23. `monitor.apply_actuals` notes still say "Family of Apps / Advertising / …", and the report footer says segments are
    manual: stale after the segment-facts lane.
24. Fiscal year end is a month; Broadcom's 52/53-week year ends 1-2 days into November in some years. Harmless for the
    discounting; an exact FY-end date would be cleaner.
25. Beta: 2-year weekly raw 2.29 (adjusted 1.86) gives a 12.5% WACC; the template's method, but worth a sanity note in the
    report when beta exceeds 2.

**Hand-keyed in this folder** (the zero-fallback goal was not met): everything in `source/xbrl_gap_patch.py` (1-5, 7, 8,
plus the amortisation add-backs and their forecast schedule), `--fade 0.6`, the reference multiples, the scenario anchors,
and the evidence of the `ai_revenue`, `q4_guide` and `backlog` claims. Segments and the revenue guide came from atlas
with no fallback; filing events and the consensus history worked once synced.

## Log

- 2026-10-25: onboarded through the generic path (AVGO added to atlas list LST-33DD8C7D; guidance / events / non-GAAP
  synced by hand). Fill clean (segments and guidance from atlas), then `xbrl_gap_patch.py` for the chain gaps above.
  House view Positive / 积极: 259 / 572 / 956 at $321.68, rule Add zone; 17 claims in the tracker (10 of 11 buy-side on
  track, Q4 guide pending; 3 of 6 risks on watch). Findings list written for the pipeline plan.
- 2026-10-25: skill faults fixed (findings 7-9, 12, 22): the report shows the Semiconductor Solutions / Infrastructure Software rows from the `segments` block; a null cost of debt falls back to risk-free + 1.5% with a WARNING instead of crashing the monitor; the next refill caps the extrapolated growth at ±50% a year (the +96% guided quarter's momentum), forecasts other income as net interest at TTM rates and reverts working capital from the TTM share to the reported years' median by FY+2: compare its FY2027 with this folder's `--fade 0.6` street before dropping the patch. Monitor rerun (side atlas :8001, atlas e19e336 / omni 8d540cf): 259 / 572 / 956 unchanged.
