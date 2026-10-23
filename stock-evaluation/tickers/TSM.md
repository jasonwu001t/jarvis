# TSM — TSMC (ADR) playbook

## Status

- Live folder: `~/AlphaResearch/research/TSM/` (`inputs.json`, `narrative.py`, `source/edgar/` (parsed 6-K releases),
  `source/meitou_*.zh.md` (local only), `reports/`). Calendar fiscal year; latest reported Q3 2026 (2026-10-15).
- Built 2026-10-23 on the 美投 (jdbinvesting.com) TSM method: valuation video 2026-08-18, 5+2 (2026-09-30 refresh,
  2026-04-23 original), Q2 research 2026-07-27, view update 2026-10-20. Next print: Q4 2026 in mid-January 2027.
- **Data path is different**: TSMC is a 20-F filer, so atlas has no XBRL, no price series, no calendar and no insider
  data for TSM (`/api/v1/filings/ticker/TSM` and `/market/prices/TSM` return 404). Actuals are parsed from the
  quarterly results press releases on EDGAR (6-K exhibits `a<q><yy>e_withguidance…htm`): USD revenue, gross /
  operating / net margins, NT$ net income converted at the release's implied rate (NT$ revenue ÷ US$ revenue), EPS per
  ADR (→ ADR share count), and next-quarter guidance (US$ revenue range, GM and OPM bands). `source/edgar/parsed.json`
  holds the parsed quarters; the build script lives in this session's history (re-create from the parsed file).
  Capex: 美投/TSMC annual dollar figures ($29.8bn 2024, $40.9bn 2025, $60–64bn 2026 guide) split pro rata.
  D&A ≈ 12.5% of revenue, SBC 0, balance sheet keyed (cash $98.4bn, LT debt $25.6bn at mid-2026): approximations
  that do not enter the no-bridge valuation. Price keyed by hand (`market.price`); `beta_mode manual`.
- The monitor prints live-fetch errors for price/closes/insider/kpis and keeps the keyed values: expected.
- Scheduled: none. Position: none recorded.

## The method (美投 TSM, reproduced by the engine)

Exit-P/E variant: `terminal_mode "exit_pe"`, `convergence_years 0`, `valuation_date "fy_end"`, `equity_bridge false`,
`dcf_roll_forward false`, `dcf_weight 1.0`, `wacc.mode "manual"` 0.098, `market.shares_override 5186`,
`target_position 0.27` (美投's $500 target = 2027 net income consensus $113.4bn × 23x industry forward P/E, between
base and bull).

- Five explicit years FY2026–30. FY2026–28 = Bloomberg as quoted (growth 36/30/24%, margin 59.5/60%); FY2029–30 =
  美投 (growth 15%, margin 55%, capex 25%/22% of revenue; 2027–28 capex 33%/29%). FY2026 = three reported quarters +
  the Q4 outlook ($52.3–54.3bn, 56.5–58.5% OPM). Tax 15%, other income 1.5% of revenue (reproduce their $171.8bn
  2030 net income).
- Terminal = 2030 net income × 18x (5-year median), WACC 9.8%, / 5.186bn ADR-equivalents, no bridge.
- Bull/bear: growth +2pp / −1pp (2026–28) and −2pp (2029–30); margin 57% / 53% in 2029–30. **Assumption flagged**:
  those alone move the value ~±12%; the published 578 / 367 need exit P/E 20x / 16x, which the scenarios carry.
  Probabilities 25/50/25; EV sizing and overlays on (overlays degrade without closes).

Reproduction (2026-10-23, price $412.35): bear / base / bull **392 / 472 / 572**, house 499; 美投 367 / 471 / 578,
target 500. PV FCFF ≈ $300bn (theirs $314bn), TV $3.07tn (theirs $3.09tn). FY2026 revenue in the model is $176bn
(Q3 beat + Q4 guide) against their $166bn.

## Thesis (美投, 2026-10-20) and what moves it

AI infrastructure investment continues (5% penetration inflection); TSMC indispensable (80%+ of advanced foundry and
packaging; every winning chip is made there); 2nm/3nm ramp = 30%+ growth for two years (capacity 175k/250k wafers a
month by end-2027, price rises 3–5%, 2nm priced 50%+ above 3nm). Risks: semiconductor cyclicality (strong),
AI falling short (strong), hyperscaler capex uncertainty under memory inflation (strong), geopolitics (weak),
Samsung/Intel second-sourcing, depreciation lag from the late-2024 capex wave. Rating Buy, risk 1, target $500,
range $367–$578 (26Q2 321/407/500, 26Q1 299/344/435).

Proven wrong by: hyperscaler 2027 capex guided below the $1.1–1.3tn signalled or any of the five cutting; gross
margin below the 65–67% band two quarters or operating margin not recovering toward 59–60% in 2027; 2nm ramp
slipping or price rises below 3–5%.

## What to watch at each print

1. Revenue vs the guided band and the full-year growth guide (40%+ for 2026); HPC growth; 2nm/3nm share of wafer
   revenue (33% in Q2, 41% in Q3 2026).
2. Gross and operating margin vs guidance (2nm dilution 3–4pp, overseas 2–3pp); capex guide.
3. Advanced packaging (CoWoS) capacity, CPO ramp (2027–28).
4. After the print: re-run the EDGAR parse for the new release, append the quarter, update Q+1 from the outlook,
   refresh FY2026–28 from the next 美投 valuation update (quarterly) or Bloomberg; rerun. `--apply-actuals` does
   not work for TSM (no XBRL).

## Log

- 2026-10-23: built on the 美投 exit-P/E method from EDGAR releases, reproducing 392/472/572; narrative from four
  美投 pieces.
