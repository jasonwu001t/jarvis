# GOOG — Alphabet playbook

## Status

- Live folder: `~/AlphaResearch/research/GOOG/` (`inputs.json`, `narrative.py`, `source/meitou_*.zh.md` (local only),
  `reports/`). No `segments.py` yet (Alphabet's segment table is in the press-release tables, not sentences).
- Built 2026-10-23 on the 美投 (jdbinvesting.com) GOOG method: valuation video 2026-08-18, 5+2 walk-through
  2026-09-27 (mis-titled as a valuation video), Q2-2026 research 2026-08-04, TPU research 2026-09-08, view
  update 2026-10-20. Next print: FY2026 Q3 on 2026-10-28 after the close.
- Data quirk: atlas indexes Alphabet's XBRL, calendar and insider data under **GOOGL**; price and valuation are
  class C (GOOG) as 美投 tracks it. `company.filing_ticker: "GOOGL"` routes the SEC calls (monitor and filler).
- Scheduled: none. Position: none recorded.

## The method (美投 GOOG, reproduced by the engine)

Exit-P/E variant (see AMZN.md and `references/valuation-method.md`): `terminal_mode "exit_pe"`,
`convergence_years 0`, `valuation_date "fy_end"`, `equity_bridge false`, `dcf_roll_forward false`,
`dcf_weight 1.0`, `wacc.mode "manual"` 0.11, `market.shares_override 12100`.

- Five explicit years FY2026–FY2030 (20290/20300 are `consensus` annual rows). FY2026–28 = Bloomberg as quoted
  (growth 23/22/21%, margin 34/35/36%, capex $200bn / $300bn / $340bn absolute); FY2029–30 = 美投 (growth 17/16%,
  margin 36/37%, capex 30%/25% of revenue). Tax 16%, other income +$7bn a year (reproduces their $314.4bn 2030
  net income). D&A = 40% of prior-year capex (calibrated to their ~$155bn PV of 2026–30 FCFF). FY2026 H2
  quarters split the residual on last year's Q3:Q4 seasonality. Alphabet gives no guidance, so no guidance street.
- Terminal = FY2030 net income × exit P/E 20x (5-year median), WACC 11% (FactSet-based), values at end-2026,
  / 12.1bn shares, no bridge.
- Bull/bear: growth ±2pp every year, margin −1pp 2026–28 (bear) and ±2pp 2029–30. **Assumption flagged**: 美投
  says only growth and margin move, but that gives ~311/410; their 263/504 need exit P/E 17x / 25x, which the
  scenarios carry. House target position 0.84 → ≈ $480 (美投's target comes from 2027 EPS $15 × 32x industry
  forward P/E, between base and bull). Probabilities 25/50/25; EV sizing and overlays on.

Reproduction (2026-10-23, price $320.76): bear / base / bull **262 / 355 / 503**, house 483; 美投 263 / 355 / 504,
target 480. PV FCFF $152bn (theirs ~$155bn), TV $6.29tn (theirs ~$6tn), PV TV $4.14tn (theirs $4.1tn).

## Thesis (美投, 2026-10-20) and what moves it

Three reasons: Google Cloud is the direct beneficiary of the enterprise AI boom (agents, model-lab ARR, token
demand); Gemini will reach commercial grade (data, algorithms, compute, cash flow; Chinese labs have matched
Opus 4.8 so Google can); the cost card is Google's (TPU → model → cloud → tools, cheapest token at scale).
Risks: flagship-model timetable and talent war (strong), capex cash-flow pressure (strong), big-company
inefficiency (strong), consumer-entry-point migration (weak), consumer DNA vs enterprise sales (weak). Rating
Strong Buy, risk 2 (raised from 1 for model-timing volatility), target $480, range $263–$504. Catalyst they wait
for: an Opus-4.8-level Gemini within months; failure case: still behind a year later → re-underwrite.

Proven wrong by: cloud growth below the street's path or cloud margin falling two quarters while capex rises;
FY2027 capex guided >10% above $300bn without backlog growth; 美投's cloud return estimate (incremental cloud
operating profit / incremental depreciation, annualised; 30–40% in 2026) falling below ~20%.

## Company-specific data

- D&A: Alphabet files `Depreciation` year-to-date (period_start = Jan 1); the fill de-cumulates by period_end
  (Q1 as is, Q2 = H1 − Q1, …); amortisation of intangibles (~$0.3bn/q) is ignored. Working capital = NOPAT + D&A
  + SBC − OCF recomputed after D&A is in.
- Other income: Q2 2026 carried ~$98bn of equity-investment marks (pretax $139bn on $41bn of operating income);
  the forecast sets other income to $7bn/yr. FY2026 displayed net income still includes the H1 marks.
- Balance sheet: cash + marketable securities $242bn, debt $101bn (long-term debt $113bn per 美投 incl. current),
  investments $127bn (equity-method + non-marketable). Not used in the valuation (no bridge).
- Beta 2-year weekly vs SPY ≈ 1.13 adjusted (display only; WACC manual). Reference P/E: forward 20x ≈ 5-year
  average; low/high 17/27 bracket own estimates.
- Segments to add: Google Services (Search & other, YouTube ads, Network, subscriptions/platforms/devices),
  Google Cloud, Other Bets, from the press-release table; 美投 figures used meanwhile (Cloud +82% Q2 2026,
  35.6% margin).

## What to watch at each print

1. Google Cloud growth and margin (the thesis line); backlog; Gemini release cadence and benchmark standing.
2. Operating margin vs the 34% FY2026 path; capex vs $195–205bn and the FY2027 "significant growth" guide.
3. TPU: external revenue ramp (Anthropic 1 GW 2026, 3.5–5 GW 2027), inventory and working capital.
4. After the print: `monitor.py --dir … --apply-actuals`; refresh FY2026–28 from the next 美投 valuation update
   (quarterly) or Bloomberg if available; keep 2029–30 unless the thesis changes; rerun.

## Log

- 2026-10-23: built on the 美投 exit-P/E method, reproducing 262/355/503; narrative from five 美投 pieces.
