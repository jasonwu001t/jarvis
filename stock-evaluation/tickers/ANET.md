# ANET — Arista Networks, Inc. playbook

## Status

- Live folder: `~/AlphaResearch/research/ANET/` (`inputs.json`, `narrative.py`, `source/street_and_gap_patch.py`, `source/exhibits/`,
  `reports/`). Calendar fiscal year (`fiscal_year_end_month` 12). Latest reported: Q2 2026 (quarter ended 2026-06-30). Next
  print: Q3 2026 on 2026-11-03 after hours (Nasdaq EPS consensus $0.99).
- Built 2026-10-25 through the **generic path** (`new_ticker.py --fye 12` → `fill_from_atlas.py --since-fy 2023` →
  `source/street_and_gap_patch.py` → `monitor.py`), the fourth onboarding after AVGO, MU and CRWD. 美投 initiated ANET on
  2026-08-13 (view 2026-10-19: 积极, risk 2, target $235 = 42x 2027 EPS of $5.64, Bloomberg's $5.13 raised 10%); the house view
  is built from Arista's own filings with 美投 as the external frame. Scheduled: none. Position: none recorded.

## Method and the street

Template method (three-scenario DCF with 12-year convergence + P/E on quarters-5-8 **GAAP** EPS, 50/50, rate-aware multiple,
ROIC anchor, overlays). GAAP basis because stock compensation is 4% of revenue and amortisation small: GAAP and non-GAAP EPS sit
within 10% of each other.

- **No sell-side consensus.** The street is written by `source/street_and_gap_patch.py` from the 8-K of 2026-08-04: Q3 2026
  "revenue of approximately $3.3 billion" x1.05 (mean beat of the last four "approximately" guides) = $3.47bn, Q4 +5% q/q:
  FY2026 $12.85bn (+43%); FY2027 +22%, FY2028 +18%; GAAP operating margin 44.5% in the guided quarters (the 48-49% non-GAAP guide
  less SBC and amortisation), 44% in 2027 and 43% in 2028; tax 19%; other income $125m a quarter (interest on $13.3bn of cash
  and investments); shares 1,276m flat (buybacks offsetting dilution); capex 2% of revenue; working capital −3% of revenue
  (deferred-revenue inflows normalising from −10%). Quarters-5-8 GAAP EPS $5.03 (美投 2027 non-GAAP $5.64).
- Scenarios (judgement 2026-10-25): bear revenue −3pp on the guided quarters, −12pp 2027, −15pp 2028, margin −4pp / −6pp, steady
  30% / 25% ROIC, 25x; base = the street, 36% / 30%, 35x; bull +2pp / +8pp / +10pp, +2pp / +3pp, 40% / 35%, 45x. Probabilities
  30/45/25 (美投 risk 2, but the stock sits at the top of its peer group).
- Reference multiples 25x / 38x / 50x: own approximate five-year forward P/E range, not official.

First run (2026-10-25, price $172.37, beta 1.72 adjusted (raw 2.08), 10-year 5.00%, WACC 12.2%): bear / base / bull
**72 / 140 / 222**, house 140 (−19%, rule "Stretched", expected value 140, exposure 42% signal → **31%** after the volatility
overlay (realised 60-day vol 48%)); DCF leg 50 / 103 / 177, P/E leg 95 / 176 / 266. The price pays 34x base quarters-5-8 EPS,
the house's own base multiple: the P/E leg alone is the price, the DCF leg values the twelve-year fade lower. Read it as: the
franchise is as good as 美投 says and the price already pays its base multiple; the upside is growth lasting longer than a
fade from +22% (the bull case), the downside is a hyperscaler capex pause or white-box pricing reaching gross margin.

## Thesis and what moves it

Switches plus EOS, one code base across every device (the hardware-plus-software moat), and the shift to inference, which
decentralises compute and multiplies interconnect demand (美投's two factors). Q2 2026: revenue $3.04bn (+38%), product $2.61bn
(+39%), GAAP operating margin 45.4%, gross margin 62.9% (65.2% a year ago), current deferred revenue $5.1bn (from $4.0bn at year
end), $13.3bn of cash and investments, no debt. Risks: Microsoft and Meta (each above 10% of revenue) deciding the growth; Nvidia
bundling Spectrum-X with GPU allocations; white-box makers (Celestica) on price; Cisco in the enterprise; a valuation at the top
of the peer group. Proven wrong (downside) by gross margin below 60%, deferred revenue falling two quarters running, or a
hyperscaler capex guide-down; proven right by gross margin holding above 63% at +40% growth.

## Company-specific data

- One reportable segment: `sec.segment_facts` has nothing for ANET by design. The operating split is product vs service revenue
  (`ProductOrServiceAxis` disaggregation, not a segment), keyed into the `product_growth` claim from the release table.
- XBRL quirks (all patched, every one a WARNING in `_sources.notes`): the cash composite looks for `MarketableSecuritiesCurrent`
  while Arista tags `AvailableForSaleSecuritiesDebtSecuritiesCurrent` ($11.1bn, five times the cash line; tagged from 2025-06-30
  in the facts, so earlier quarters carry cash only); Q4 2025 capex not derived (`PaymentsToAcquirePropertyPlantAndEquipment`
  annual − 9M = $37m) and Q4 share counts never served (annual used); `ContractWithCustomerLiabilityCurrent` keyed as a
  `deferred_revenue` line for the `level` claim; no debt (cost of debt 5% nominal so the WACC function runs); `rpo` KPI stops at
  2022 (Arista stopped tagging it); buybacks 0 in H1 2026 (true: `PaymentsForRepurchaseOfCommonStock` 0 YTD).
- Guidance wording: "Financial Outlook For the third quarter of 2026, we expect: • Revenue of approximately $3.3 billion;
  • Non-GAAP operating margin of 48 - 49%; and • Non-GAAP diluted net income per share between $1.06 and $1.08." The
  "approximately $X" form has no range, so neither `sec.earnings_guidance` (0 rows for ANET) nor `guidance.py` gives a row;
  releases before 2025 guided revenue as a range ("between $X and $Y million"). Beat history vs "approximately": 1.050, 1.026,
  1.042, 1.084 (mean 1.05).
- Non-GAAP: `sec.earnings_non_gaap` has 442 rows for ANET (full bridge each release: SBC, intangible amortisation, tax effects);
  not needed for the GAAP basis but the right source for a non-GAAP cross-check.
- Filings worth re-reading: 8-K 2025-09-08 (Duda President and CTO, 5.02 + 8.01), 10-K FY2025 (customer concentration note:
  Microsoft and Meta; purchase commitments; the 4-for-1 split of December 2024). `sec.filing_events` has 23 rows for ANET.

## What to watch at each print (Q3 2026, 2026-11-03)

1. Revenue against "approximately $3.3bn" and the street's $3.47bn; product growth against +30%.
2. Gross margin against the 60% floor (62.9% in Q2, 65.2% a year ago): the filed evidence on white-box and Nvidia pricing.
3. Non-GAAP operating margin against 48-49% (GAAP floor 42%); deferred revenue against $5.1bn.
4. Any change in the Microsoft / Meta concentration language; AI back-end and front-end revenue commentary; the 2027 outlook
   (Arista gives it in November).
5. Buybacks: none in H1 2026 against $1.6bn in 2025; the street holds the count flat.

## Findings: where the generic path fell short (2026-10-25)

"Raw" the fill produced a momentum street (+33% fading 80%/yr: FY2027 +26%, FY2028 +21%), cash understated by $11bn (no AFS
securities), no Q4 2025 capex or share count, forecast other income 0 and a null cost of debt (monitor crash).

**atlas KPI chains / `research/fundamentals`**
1. The cash composite misses `AvailableForSaleSecuritiesDebtSecuritiesCurrent` ($11.1bn): the equity bridge would have carried
   $2.3bn of cash for a company with $13.3bn (MU 3 again, bigger here). Fix: AFS tags in the cash chain.
2. Q4 capex not derived (`capex` missing 20234, 20244, 20254) although the 9M YTD and annual rows exist; Q4 share counts never
   served (MU 1). Fix: derive Q4 for every flow KPI from annual − 9M; serve Q4 share averages from the 10-K.
3. `rpo` stops at 2022 (Arista stopped tagging `RevenueRemainingPerformanceObligation`); the demand indicator is deferred revenue
   (`ContractWithCustomerLiabilityCurrent`), which is not a KPI. Fix: a `deferred_revenue` KPI.
4. Product vs service revenue (`ProductOrServiceAxis`) is not in `sec.segment_facts` (business segments only). Fix: ingest the
   revenue-disaggregation axis as a second segment family, so single-segment filers still get a split.

**`fill_from_atlas.py` / `new_ticker.py`**
5. "Revenue of approximately $3.3 billion" (no range) gives no row in either parser (AVGO 15-17, MU 9, CRWD 7: a fourth form).
   Fix: accept a point guide ("approximately $X") as low = high = X; the "between $X and $Y" form of the older releases too.
6. Beat history keyed by hand (1.05 over four) for the same reason.
7. `pretax_cost_of_debt` null → crash (AVGO 7, MU 11, CRWD 10); for a no-debt filer the fill should write a nominal rate and say so.
8. Forecast `other_income` 0 (AVGO 8, MU 12, CRWD 11): $0.5bn a year of interest income here, 7% of pretax.
9. Working capital: the TTM derivation gives −10% of revenue (deferred-revenue inflows of a company growing 38%) and the fill
   carries it as a permanent inflow; the patch uses −3%. Fix: scale working capital to revenue growth (CRWD 12).
10. The momentum street's margin is the TTM GAAP margin (43%) while the company guides non-GAAP (48-49%); without the non-GAAP
    bridge in the street the guided quarter's margin is 4pp low. Fix: read the non-GAAP margin guide and the `sec.earnings_non_gaap`
    SBC line to convert it.

**omni datasets**
11. `sec.earnings_non_gaap`: 442 rows, works for ANET's bridge format (unlike AVGO and MU). `sec.filing_events`: 23 rows, current.
12. `nasdaq.earnings`: consensus $0.99 with no revisions over 15 captures: fine.

**skill (report, engine, monitor, tracker)**
13. `report_html.ROW_SPECS` hard-codes META's segments (AVGO 22): the product/service split cannot be shown as rows.
14. The "Starting reinvestment rate > 0" check warns (！) in every scenario because capex (2%) + working capital (negative) sits
    below D&A: a deferred-revenue business reinvests through working capital, which the check reads as negative reinvestment.
    Fix: treat a negative working-capital build as reinvestment only when positive, or exempt asset-light models.
15. Monitor footer: "segments are manual" (AVGO 23).

**Hand-keyed in this folder**: everything in `source/street_and_gap_patch.py` (findings 1-3, 5-9 and the whole street), the
scenario anchors, the reference multiples, the evidence of the `product_growth`, `q3_guide`, `buyback`, `concentration` and
`competition` claims. From atlas with no fallback: the fundamentals route (every flow line, FY2023-26), filing events (23 rows),
the non-GAAP rows, the consensus history, the price and beta inputs.

## Log

- 2026-10-25: onboarded through the generic path (ANET added to atlas list LST-33DD8C7D, collected at once as an S&P 500 name).
  Fill, then `street_and_gap_patch.py` (AFS cash, Q4 2025 capex and shares, deferred revenue line, guidance street). House view
  Watch / 观察: 72 / 140 / 222 at $172.37, rule Stretched, exposure 31% after the vol overlay; 14 claims (9 on track, 3 watch,
  1 broken: the price rule, 1 pending). 美投 积极 $235 = 42x 2027 EPS: the disagreement is the DCF leg's fade, not the business.
  Findings list written for the pipeline plan.
- 2026-10-25: skill faults fixed (findings 7-9, 13, 14): checks use the deferred-revenue rule (detected: median working-capital build -1.4% of revenue, FY2022-25); the starting-reinvestment check still warns, now because capex less D&A (1.0-1.3% of revenue) sits below the 3.2-3.4% a 30% steady ROIC needs, not because of the working-capital release. Monitor rerun: 72 / 140 / 222 unchanged.
