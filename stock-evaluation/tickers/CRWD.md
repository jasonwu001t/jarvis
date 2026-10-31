# CRWD — CrowdStrike Holdings, Inc. playbook

## Status

- Live folder: `~/AlphaResearch/research/CRWD/` (`inputs.json`, `narrative.py`, `source/street_and_gap_patch.py`, `source/exhibits/`,
  `reports/`). Fiscal year ends January 31 (`fiscal_year_end_month` 1; FY2027 ends 2027-01-31). Latest reported: Q2 FY2027
  (quarter ended 2026-07-31). Next print: Q3 FY2027 on 2026-12-01 (Nasdaq's EPS consensus reads $0.00 after the split).
- Built 2026-10-25 through the **generic path** (`new_ticker.py --fye 1` → `fill_from_atlas.py --since-fy 2024` →
  `source/street_and_gap_patch.py` → `monitor.py`), the third onboarding after AVGO and MU and the first loss-making GAAP filer.
  美投 initiated CRWD on 2026-10-19 (5+2 of 2026-10-05; 积极, risk 4, target $309; the CRWD-vs-PLTR playbook of 2026-09-30);
  the house view is built from CrowdStrike's own filings with 美投 as the external frame, and disagrees on the rating.
  Scheduled: none. Position: none recorded.

## Method and the street

Template method (three-scenario DCF with 12-year convergence + P/E on quarters-5-8 **adjusted** EPS, 50/50, rate-aware multiple,
ROIC anchor, overlays). `earnings_basis "adjusted"` here means the company's **non-GAAP** basis (SBC and amortisation of acquired
intangibles added back after a 22.5% notional tax), not the AMD convention, because GAAP operating income is negative (−2% in
Q2 FY2027) and the AMD basis would leave no earnings for the P/E leg. The DCF still charges stock compensation (FCFF = NOPAT + D&A
− capex − working capital with SBC inside operating income), which is why the two legs disagree by a factor of three.

- **No sell-side consensus.** The street is written by `source/street_and_gap_patch.py` from the 8-K of 2026-08-26: Q3 FY2027
  revenue $1,523.2-1,529.2m and FY2027 $5,991.1-6,011.1m, midpoints x1.015 (mean beat of the last six quarterly guides), Q4 =
  FY guide less H1 less Q3: FY2027 $6.05bn (+26%); FY2028 +26% and FY2029 +23% (ending ARR +25%, net new ARR guided +34%);
  non-GAAP operating margin 24.5% / 25% / 27% / 29% (FY2027 guide $1,497-1,508m = 25%); GAAP = non-GAAP less SBC (23% of revenue
  easing to 19%) and amortisation ($13m a quarter); GAAP tax 20%; other income $45m a quarter; shares 1,045m rising ~1.5% a
  year; capex 8% of revenue; working capital −6% of revenue (deferred revenue). Quarters-5-8 non-GAAP EPS $1.90.
- Scenarios (judgement 2026-10-25): bear revenue −2pp on the guided quarters, −6pp FY2028, −10pp FY2029, margin −3pp / −5pp,
  steady 18% GAAP margin / 20% ROIC, 60x; base = the street, 28% / 25%, 90x; bull +1pp / +5pp / +8pp, +2pp / +4pp, 36% / 30%,
  120x. Probabilities 30/45/25. The steady GAAP margins assume SBC falls to the 8-12% of mature security software.
- Reference multiples 55x / 85x / 130x: own approximate forward non-GAAP P/E range since 2021, not official.

First run (2026-10-25, price $257.57, beta 1.44 adjusted (raw 1.66), 10-year 5.00%, WACC 11.0%): bear / base / bull
**58 / 109 / 176**, house 109 (−58%, rule "Stretched", expected value 110, exposure 32% signal → **15%** after the volatility
overlay (realised 60-day vol 71%)); DCF leg 19 / 47 / 93, P/E leg 97 / 171 / 259. The price pays 136x base quarters-5-8 non-GAAP
EPS and 45x FY2027 revenue; the bull P/E leg alone (120x) reproduces it. Read it as: the business is doing what 美投 says
(ARR +25%, net new ARR +51%, Flex +101%, 30% FCF margin) and the price already assumes the agent-security market is as large as
endpoint security; 美投's own caveat ("little valuation margin for error") is the house view's rating.

## Thesis and what moves it

Sensors next to the operating system make CrowdStrike the vendor-agnostic place to secure AI agents as they proliferate and
fragment (美投's two factors); Falcon Flex consumption contracts are where the agent modules land. Costs lead revenue (capex
before renewals), so capex is 美投's leading indicator of a gross-margin dip and recovery. Risks: the labs (OpenAI, Anthropic)
and Microsoft pulling security into their platforms; the agent route centralising instead; SBC at 23-26% of revenue; dilution
(+4.5% y/y); a crowded AI-software trade. Proven wrong (on the upside) by GAAP operating profit for two quarters with SBC under
20% of revenue, or the price falling toward the base value with ARR growth intact; proven right by net new ARR falling y/y,
Flex growth halving, or a large customer adopting a lab's or Microsoft's agent security in place of Falcon.

## Company-specific data

- One reportable segment: `sec.segment_facts` has nothing for CRWD by design. The operating split is subscription ($1,400m) vs
  professional services ($71m) on the income statement, and ARR / net new ARR / Flex ARR in the release prose (press-release
  KPIs, not XBRL): keyed into the `arr`, `flex` and `ng_margin` claims each quarter.
- XBRL quirks (all patched, every one a WARNING in `_sources.notes`): the 4-for-1 split of 2026-07-01
  (`StockholdersEquityNoteStockSplitConversionRatio1` = 4 at 2026-06-03) leaves pre-split quarters as filed (251m) beside restated
  comparatives (1,000m); Q4 FY2026 served revenue and capex only (operating income, pretax, tax, net income, other income
  derived from the 10-K annual); `DepreciationDepletionAndAmortization` tagged in the Q2 10-Qs only (other quarters at 1.75%
  of revenue); `rpo` served ($10.7bn) but not carried (keyed); interest expense $27m TTM on the $750m 3% notes (3.6%).
- Guidance wording: a two-column table "Q3 FY27 Guidance / Full Year FY27 Guidance" with rows "Annual recurring revenue",
  "Total revenue $1,523.2 - $1,529.2 million $5,991.1 - $6,011.1 million", "Non-GAAP income from operations", "Non-GAAP net
  income", "Non-GAAP net income per share". Neither `sec.earnings_guidance` (0 rows for CRWD) nor `guidance.py` reads it. Beat
  history vs the midpoint: 1.018, 0.997, 1.014, 1.012, 1.017, 1.022 (mean 1.015).
- Non-GAAP: `sec.earnings_non_gaap` has 116 rows for CRWD (operating income and margin GAAP/non-GAAP per release, some
  adjustment lines); used as the cross-check for the adjustments line ($404.9m of operating adjustments in Q2 FY2027 vs $390.2m
  from SBC + amortisation: the gap is payroll taxes on equity awards and acquisition costs).
- Filings worth re-reading: 8-K 2026-06-03 (split, Item 8.01), the July 19, 2024 incident 8-Ks and the customer-commitment
  packages (credits of $14.5m in Q2 FY2027), 10-K FY2026 (ARR definition, concentration, the $750m notes).
  `sec.filing_events` has 34 rows for CRWD.
- Nasdaq's consensus EPS for the next report date reads $0.00 on 12 estimates (post-split artefact): the `eps_consensus`
  claim stays pending until the vintages carry a number.

## What to watch at each print (Q3 FY2027, 2026-12-01)

1. Revenue against $1,523-1,529m and the street's $1,549m; net new ARR against $333m and the +34% FY guide; ending ARR against
   the ~$6.6bn FY2027 path.
2. Non-GAAP operating income against $373-376m (25%); GAAP operating margin against the street's +0.7% (the `gaap_breakeven`
   claim is broken until it turns positive).
3. Falcon Flex ARR and module adoption (the agent-security vector); any lab or Microsoft agent-security launch named on the call.
4. Gross margin against the 73% floor and capex against 10% of revenue (美投's leading indicator).
5. SBC as a share of revenue (25.6% in Q2) and the diluted count (1,044m).

## Findings: where the generic path fell short (2026-10-25)

"Raw" the fill produced a momentum street (+24% fading) on a −2.5% GAAP margin, so every scenario had negative net income
and the P/E leg was meaningless; the model also had no Q4 FY2026 income statement, share counts off by 4x before July 2026,
D&A for two quarters only, and a null cost of debt.

**atlas KPI chains / `research/fundamentals`**
1. The 4-for-1 split is in the facts (`StockholdersEquityNoteStockSplitConversionRatio1` = 4, 2026-06-03) and not applied:
   pre-split quarters (251m shares) sit beside restated comparatives (1,000m) (AVGO 4 again). Fix: apply the ratio fact (or
   `alpaca.corporate_actions`) to share and per-share KPIs before the split date.
2. Q4 FY2026 derived for revenue and capex only: `operating_income`, `pretax_income`, `income_tax_expense`, `net_income` and the
   other-income composite are blank for 20264 though the 10-K annual and the three 10-Q quarters exist. Fix: derive Q4 for every
   flow KPI whose annual and Q1-Q3 (or 9M YTD) rows exist.
3. `depreciation_amortization` served for Q2 10-Qs only (`DepreciationDepletionAndAmortization` 3M + 6M); Q1/Q3/Q4 blank. Fix:
   derive quarters from YTD rows (Q1 = 6M − Q2's 3M; Q3 = 9M − 6M) and the annual.
4. `rpo` served and not carried (AVGO 13, MU 5): keyed.
5. No `arr` KPI: ARR is a press-release metric. Fix: `sec.earnings_press_release_figures` could parse "Annual Recurring Revenue
   (ARR) grew 25% year-over-year to $5.84 billion" and "net new ARR … $332.8 million" (a KPI allowlist per issuer).

**`fill_from_atlas.py` / `new_ticker.py`**
6. For a GAAP loss-maker the momentum street carries the negative margin forward and the P/E leg goes negative; nothing in the
   fill or the scaffold switches to a non-GAAP basis or warns. Fix: when TTM GAAP margin < 0 and `sec.earnings_non_gaap` has a
   non-GAAP operating income, build the adjustments line from it and set `earnings_basis` with a WARNING.
7. The guidance table (two columns, four rows) is not read by `sec.earnings_guidance` or `guidance.py` (AVGO 15-17, MU 9 again,
   a third form). Fix: a table-layout reader for "<metric> $a - $b million $c - $d million" with the column headers as periods.
8. Beat history keyed by hand (1.015 over six) for the same reason.
9. Q4-of-last-FY lines missing from the fill's history (finding 2) propagate: the FY2026 annual existed, but TTM margin and ROIC
   read a blank Q4 as zero.
10. `pretax_cost_of_debt` null → crash (AVGO 7, MU 11).
11. Forecast `other_income` 0 (AVGO 8, MU 12): $45m a quarter of interest income here.
12. The street's working-capital line (−10% of revenue from the TTM derivation) is a large permanent inflow for a deferred-revenue
    business; the patch uses −6%. Fix: tie the forecast working capital to revenue growth, not level.

**omni datasets**
13. `sec.earnings_non_gaap` works for CRWD (116 rows) and gave the cross-check; it has no net-income or EPS rows for most
    releases (the "Non-GAAP net income attributable to CrowdStrike" bridge), so the adjustments line still came from XBRL.
14. `nasdaq.earnings` consensus EPS $0.00 on 12 estimates after the split: the vintage is wrong, and the `consensus_revision`
    claim cannot score. Fix: treat 0.00 with estimates > 0 as missing, and re-base vintages across a split.
15. `sec.filing_events`: 34 rows, current (S&P 500 cron universe); the split 8-K is an 8.01 (headline regex option, AVGO 21).

**skill (report, engine, monitor, tracker)**
16. Two earnings bases in one model (DCF on GAAP with SBC as a cost, P/E on non-GAAP) is the right economics but the report
    does not say which leg uses which; the "price-implied P/E" line labels the EPS "GAAP". Fix: label the basis per leg.
17. The `margin` claim kind's `tolerance` is relative to `min`, so a `min` of 0 (GAAP break-even) has no near-miss band:
    −2.3% scores Broken, not Watch. Fix: an absolute `band` option.
18. The regime/vol overlays cut exposure to 15% for a name whose house value is below the price anyway; the report could say
    the rule ("Stretched", 25%) and the overlay agree. Cosmetic.
19. `report_html.ROW_SPECS` hard-codes META's segments (AVGO 22): harmless here (one segment) but the subscription/services split
    cannot be shown as rows.
20. Monitor footer: "segments are manual" (AVGO 23).

**Hand-keyed in this folder**: everything in `source/street_and_gap_patch.py` (findings 1-4, 6-12 and the whole street), the
scenario anchors, the reference multiples, the evidence of the `arr`, `flex`, `ng_margin`, `q3_guide` and `labs_security`
claims. From atlas with no fallback: the fundamentals route (revenue, gross profit, cash flow, balance sheet, SBC, RPO), filing
events (34 rows), the non-GAAP rows (cross-check), the consensus history (broken value), the price and beta inputs.

## Log

- 2026-10-25: onboarded through the generic path (CRWD added to atlas list LST-33DD8C7D, collected at once as an S&P 500
  name). Fill, then `street_and_gap_patch.py` (split, Q4 FY2026, D&A, non-GAAP adjustments, guidance street). House view
  Cautious / 谨慎 on valuation (business on track): 58 / 109 / 176 at $257.57, rule Stretched, exposure 15% after the vol overlay;
  16 claims (10 on track, 2 watch, 2 broken: GAAP break-even and the price rule, 2 pending). 美投 积极 $309: the disagreement is
  the multiple, not the business. Findings list written for the pipeline plan.
- 2026-10-25: skill faults fixed (findings 6, 10-12, 17, 19): checks use the deferred-revenue rule (detected: median working-capital build -16.5% of revenue) and the three starting-reinvestment warnings clear; `gaap_breakeven` (min 0, tolerance 0.05) scores Watch at -2.3% instead of Broken; a negative or near-zero earnings base now turns that scenario's P/E leg off with a WARNING (not triggered here: the basis is adjusted). Monitor rerun: 58 / 109 / 176 unchanged.
