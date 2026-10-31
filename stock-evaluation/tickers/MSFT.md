# MSFT — Microsoft playbook

## Status

- Live folder: `~/AlphaResearch/research/MSFT/` (`inputs.json`, `narrative.py`, `source/meitou_*.zh.md` (local only),
  `reports/`). Fiscal year ends June (`fiscal_year_end_month: 6`); FY2026 (to June 2026) is reported.
- Built 2026-10-23 on the 美投 (jdbinvesting.com) MSFT method: valuation video 2026-08-06, 5+2 walk-through
  2026-08-30, FY26Q4 earnings research 2026-08-01, Copilot research 2026-06-08, view update 2026-09-17. Next print:
  FY2027 Q1 on 2026-10-28 after the close.
- No `segments.py` (Microsoft reports three segments in tables; Azure growth is given in the call, not XBRL).
  Microsoft gives quarterly guidance on the call only, so no guidance street.
- Scheduled: none. Position: none recorded.

## The method (美投 MSFT, reproduced by the engine)

Exit-P/E variant: `terminal_mode "exit_pe"`, `convergence_years 0`, `valuation_date "fy_end"` (= the balance-sheet
date here), `equity_bridge false`, `dcf_roll_forward false`, `dcf_weight 1.0`, `wacc.mode "manual"` 0.113,
`market.shares_override 7430`, `target_position 0.0` (美投's $599 target is its base case).

- Four explicit years FY2027–FY2030. FY2027–28 = Bloomberg/Wall Street as quoted (growth 20.5/22.5%, margin
  47.1/47.8%, capex = FY2026's ~$141bn incl. finance leases +$60bn then +$50bn); FY2029–30 = 美投 (growth
  19.2/17.7%, margin 46.5/46.0%, capex 44%/41.5% of revenue). Tax 18%, other income +$15bn (reproduces their
  $272bn FY2030 net income). D&A = 24% of prior-year capex (calibrated to their ~$20bn PV of FY2027–30 FCFF).
  Forecast capex carries leases inside `capex` (finance_lease_additions 0).
- Terminal = FY2030 net income × 25x (2005–2025 average; bull 27x, bear 22x, as stated), WACC 11.3% (average of
  Bloomberg 13.3% and FactSet 9.34%), / 7.43bn shares, no bridge.
- Bull/bear exactly as the video: growth ±0.5pp FY2027–28 and ±2pp FY2029–30; margin ±0.5pp FY2027–28 and ±1pp
  FY2029–30; exit P/E 27x / 22x. Probabilities 25/50/25; EV sizing and overlays on.

Reproduction (2026-10-23, price $521.08): bear / base / bull **493 / 598 / 689**, house 598; 美投 491 / 599 / 691,
target 599. TV $6.79tn (theirs ~$6.8tn), PV $4.42tn (theirs $4.4tn), PV FCFF $24bn (theirs ~$20bn).

## Thesis (美投, 2026-09-17) and what moves it

"Risk release, not new growth": three doubts (Azure not accelerating; cloud margin slipping without in-house
silicon; software disrupted by AI agents). FY26Q4 answered the first (Azure 43%, guided 45%, capacity +120% y/y,
orders ex-OpenAI +18%, RPO +25%); software sentiment partly repaired; the margin doubt waits for Maia 300 in
2H-2027. Long-term: enterprise AI "C-position" (Azure + multi-model Copilot), an ecosystem too costly to leave,
AI upside into the second-largest cloud. Risks: M365 disrupted (strong), Azure margin falling (strong), capex
rising again (strong), clouds degrading to compute pipes (weak). Rating Strong Buy, risk 2, target $599, range
$491–$691 (26Q2 485/584/669, 26Q1 462/534/578, 25Q4 479/533/585).

Proven wrong by: Azure back below 40% while capex rises or the 45% acceleration not arriving; Intelligent Cloud
margin falling two quarters; M365 commercial seats below +6% or Copilot net adds stalling; FY2027 positive-FCF
promise withdrawn or FY2027 capex >10% above the path.

## Company-specific data

- D&A: Microsoft files `Depreciation` year-to-date from July 1; the fill de-cumulates by period_end (Sep = Q1,
  Dec − Sep = Q2, …, Jun = FY). Amortisation of intangibles is not included. Working capital recomputed as
  NOPAT + D&A + SBC − OCF afterwards.
- Capex: XBRL PP&E additions (FY2026 $116bn) exclude finance leases ($25bn); 美投's "$150bn" is the all-in figure.
  The forecast carries the all-in number in `capex`.
- Other income: FY2026 Q2 carried ~$10bn of non-operating gains (OpenAI-related marks); the forecast uses $15bn/yr.
- XBRL has no FY2026 Q4 diluted share count (filled from Q3). Beta ≈ 1.08 adjusted (display only).
- Reference P/E: 美投's history 12x (pre-2010) → 15x (2015) → 25x (2020) → 30x (2020–25) → 22x after the 2026
  software sell-off; 25x = 20-year average = exit multiple.

## What to watch at each print

1. Azure growth (43% → 45% guided) and the capacity ramp; RPO and bookings ex-OpenAI.
2. Intelligent Cloud margin (gross margin, not just operating), Maia 300 timing.
3. M365 commercial seats (+6%), Copilot paid seats (30m+) and GitHub Copilot usage revenue.
4. Capex vs the FY2027 positive-FCF promise; lease accounting changes are not spending cuts.
5. After the print: `monitor.py --dir … --apply-actuals`; refresh FY2027–28 from the next 美投 valuation update
   (quarterly) or Bloomberg; keep FY2029–30 unless the thesis changes; rerun.

## Log

- 2026-10-23: built on the 美投 exit-P/E method, reproducing 493/598/689; narrative from five 美投 pieces.
- 2026-10-25: the checks now use the deferred-revenue rule (detected: median working-capital build -1.3% of revenue, FY2022-26, the unearned-revenue model): a working-capital release is not counted against the reinvestment checks; declare `company.business_model: "standard"` to switch it off. Monitor rerun: 493 / 598 / 689 unchanged.
