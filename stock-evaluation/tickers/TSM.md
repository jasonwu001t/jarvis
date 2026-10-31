# TSM — TSMC (ADR) playbook

## Status

- Live folder: `~/AlphaResearch/research/TSM/` (`inputs.json` built by `source/build_from_template.py` from the 美投 workbook,
  `narrative.py`, `source/edgar/` (parsed 6-K releases), `source/meitou_*` (transcripts and the Excel, local only),
  `method_v1.37_and_data_gaps_2026-10-24.md`, `reports/`). Calendar fiscal year; latest reported Q3 2026 (2026-10-15).
  Next print: Q4 2026 in mid-January 2027.
- **2026-10-24: moved to 美投's unified template** (美投估值模板 TSM v1.37, 2026-10-21, the META template; TSM is the second
  name on it). The August exit-P/E build is kept as `source/inputs_exitpe_2026-08-18.json`.
- **Data path (2026-10-25)**: TSM is on the atlas watchlist (prices, filings, beta live). The actual periods come from atlas:
  6-K results exhibits via `sec.foreign_quarterly_statements` (2025 Q1–2026 Q3, FY2025 summed) and the 20-F's IFRS XBRL
  (FY2024), applied by `source/apply_atlas_history.py` after `build_from_template.py`; the template's rows stay under
  `_replication` with a parity table (flows within 0.4%, see the method note §5). The forecast block is still Bloomberg
  consensus as pasted in the template (not official), dated in `as_of`; DPS, minority, total debt, SBC and the segment
  display lines are template rows named as WARNINGs in `_sources.notes`.
- Scheduled: none. Position: none recorded.

## The method (美投 unified template, reproduced to $0.20)

Standard template settings: `terminal_mode gordon`, `convergence_years 12`, `valuation_date balance_sheet`, `equity_bridge`
and `dcf_roll_forward` on, `dcf_weight 0.3` (TSM-specific: 30% DCF / 70% P/E for cyclicality), `earnings_basis gaap`
(IFRS, no adjusted EPS), `multiple_rate_aware` and `steady_roic_anchor` off (the template has neither), `wacc.mode manual`
0.1130 (rf 5.0%, ERP 4.94% NYU incl. Taiwan premium, β 1.296 Bloomberg-adjusted, Kd 4.2%), `target_position 0`.

- Explicit FY2026 Q4–FY2028 on Bloomberg consensus; adjustments on FY2027E and FY2028E: total revenue growth
  −3 / +1 / +5 pp and gross margin −2 / +1 / +3 pp (keyed as "Operating margin" pp: the template applies gross-margin pp
  exactly as operating-margin pp). Steady state g 3.5%; ROIC 18 / 22 / 25% (history 22–32%, cycle lows 22–23%, today 60%+);
  operating margin 35 / 40 / 45% (2019 low ~35%, normal 40%+, today ~60%). P/E 15 / 18 / 20x on quarters-5-8 EPS
  ($28.54 base) against the own 5-year BF range 14.6 / 17.5 / 20.4x (current 17.6x).
- **Key the raw Bloomberg rows (计算 AE..AQ), not the 预测 sheet**: 预测 already carries the base-case deltas; keying it
  double-applies the adjustments (410 / 556 / 703 instead of 394 / 535 / 676).

Reproduction (price $414.44, 2026-10-22): bear / base / bull **394 / 535 / 676** (DCF 412 / 584 / 804, P/E 386 / 514 /
621), house 535; template 393.89 / 534.73 / 675.86, target $535 (+29%), rating 积极. Checks: FRED DGS10 on the
balance-sheet date was 5.29%, not the template's 5.0% (base 528 at 5.29%); our own 2y weekly beta vs SPY to 2026-09-30 is
1.43 raw / 1.29 adjusted, matching Bloomberg.

## Thesis (美投, 2026-10-21) and what moves it

AI-driven growth, visible now in cloud demand for leading-edge wafers and advanced packaging, later in edge-AI silicon;
technology, capital and customer moats let TSMC capture the industry's growth: high upside, well-supported downside. Buy
reasons: management promoted from within; secure leading position (whichever chip wins is made at TSMC); AI moving to
devices; hyperscaler capex confirmed; 2nm/3nm capacity, yields and prices for two years. Risks: semiconductor cyclicality
(the reason for the 30% DCF weight), AI falling short, geopolitics (only the ERP's country premium allows for it),
hyperscaler capex budgets breaking, Samsung/Intel share, depreciation from the late-2024 capex arriving in 2H 2026.

Ten thesis claims in `inputs.json`: revenue growth ≥30% y/y, operating margin ≥56.5%, HPC ≥60% of wafer revenue and the
Stretched rule are auto-scored; node ramp, capex returns, hyperscaler capex, cycle, geopolitics and "consensus vs guide"
are manual with due dates (next print 2027-01-15).

## What to watch at each print

1. US$ revenue and the guide (Q4: $52.3–54.3bn, GM 65–67%, OPM 56.5–58.5%) against Bloomberg's $51.8bn; 2nm and 3nm share
   of wafer revenue (8% / 33% in Q3), HPC share (68%), wafer shipments.
2. Gross margin against the 2nm-ramp and overseas-fab dilution (3–4pp + 2–3pp); operating margin recovery toward 60%.
3. Capex guide for 2027 and depreciation; hyperscaler 2027 capex guides.
4. After the print: the 6-K lands in atlas within a day (`sec.foreign_quarterly_statements`); run the monitor with
   `--apply-actuals` (6-K quarters now flow through the fundamentals route), or re-run `source/apply_atlas_history.py`
   for the whole history; when 美投 releases the next template, drop it in `source/`, run `build_from_template.py` then
   `apply_atlas_history.py`. Minority interest and DPS for the new quarter stay hand-keyed (not in the 6-K).

## Log

- 2026-10-23: built on the 美投 exit-P/E method (2026-08-18 video), 392 / 472 / 572.
- 2026-10-24: rebuilt on the unified template v1.37 from the workbook and the 2026-10-21 video: 394 / 535 / 676, exact
  to $0.20; narrative rewritten; ten claims; method-and-data-gaps note written.
- 2026-10-25: TSM added to the atlas watchlist (list API, 5 jobs): prices (600 days), 6-K/20-F filings and the dynamic universe now flow; monitor switched to CAPM with the live adjusted beta (1.294 vs template 1.296, WACC 11.28%), live price, overlays active; rf kept at the template 5.0%. Targets unchanged 394/535/676.
- 2026-10-25: `source/company_targets.json` (Q4 2024 call outlook, unverified) and a `target_vs_model` claim; the monthly revenue 6-Ks show in the material-filings list (no item codes on 6-Ks).
- 2026-10-25: monitor reads `/research/fundamentals/TSM?currency=USD` (company_type ifrs, per_share_divisor 5 from the list item): annual IFRS only (no quarterly XBRL), so the quarterly history stays on the template rows; no segment facts for 20-F/6-K yet.
- 2026-10-25: `consensus_revision` claim keyed; pending until Nasdaq lists the January date.
- 2026-10-25: history rebuilt from atlas's 6-K / 20-F rows (`source/apply_atlas_history.py`); template rows kept under `_replication` with parity: flows 0.37% worst (FX), parent equity 0.2%, derived shares 0.03%; targets at the template price 393.88 / 534.71 / 675.86 vs 393.86 / 534.68 / 675.81. Monitor at $418.51: 394 / 535 / 676, WACC 11.28%. Noted: 20-F FY2024 (IASB IFRS) net income 1.2% below Bloomberg's T-IFRS row; 6-K long-term investments 28–33% above the template's 2025 rows, equal in Q3 2026.
- 2026-10-25: the report's model table now shows Chips (HPC, Smartphone, IoT, Automotive, Other platforms indented under it) and Other from the `segments` block (skill fix: the rows were META's). Monitor rerun: 394 / 535 / 676 unchanged.
