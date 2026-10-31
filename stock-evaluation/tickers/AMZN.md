# AMZN — Amazon.com playbook

## Status

- Live folder: `~/AlphaResearch/research/AMZN/` (`inputs.json`, `narrative.py`, `segments.py`, `guidance.json`,
  `source/exhibits/`, `source/meitou_*.zh.md` (local only), `reports/`).
- Built 2026-10-22 by the skill from SEC XBRL (FY2023 → FY2026 Q2), the 8-K press releases (guidance and
  segment sentences) and Alpaca bars; **rebuilt the same day on the 美投 (jdbinvesting.com) AMZN method**
  (valuation video 2026-09-17, "5+2" walk-through 2026-10, view update 2026-10-18, deep-dive 2025-12-01).
  Next print: FY2026 Q3 on 2026-10-29 after the close.
- Scheduled: none (run `monitor.py --dir research/AMZN` by hand, or add a `bin/schedule/job` case).
- Position: none recorded (`monitor.current_exposure` null).

## The method (美投 AMZN, reproduced by the engine)

Not the META template. Switches in `inputs.json`: `blend.terminal_mode "exit_pe"`, `convergence_years 0`,
`valuation_date "fy_end"`, `equity_bridge false`, `dcf_roll_forward false`, `dcf_weight 1.0`,
`wacc.mode "manual"` (0.138), `market.shares_override 10783`. See `references/valuation-method.md`.

- Six explicit years FY2026–FY2031 (periods 20290/20300/20310 are `consensus` annual rows). Three drivers:
  revenue, operating margin, capex. FY2026–28 = Bloomberg consensus as quoted in the video (growth
  15.6/14.6/15.0%, margin 13.3/14.8/16.4%, capex/revenue 26.6/29.4/27.6%); FY2029–31 = 美投 (15/14/13%,
  17.9/19.4/20.9%, 25%). Tax 20%. Other income 0 (Anthropic marks excluded). D&A = 60% of the prior year's
  capex (calibrated so the PV of 2026–31 FCFF lands near their +$47.5bn; they did not publish D&A).
  FY2026 Q3 = the company guidance street; Q4 = the residual that closes the Bloomberg year.
- Terminal value = FY2031 net income × exit P/E (bear 20x / base 22x / bull 24x), discounted at a fixed
  13.8% WACC; present values stated at end-2026; DCF total / 10,783m shares, no net-debt bridge.
- Bull/bear = growth ±1pp in 2027–28, ±2pp in 2029–31; margin path ±1pp / ±2pp (`adjustments`).
- House target = base + 0.65 × (bull − base) ≈ 美投's 12-month target $350. Probabilities 25/50/25;
  EV sizing and overlays on; rate-aware multiple and ROIC anchor off (no steady state in this mode).
- The quarters-5-8 P/E leg (25/30/34x) is computed and shown but carries 0% weight.

Reproduction (2026-10-22, price $262.37): bear / base / bull **219 / 294 / 384**, house 352, against
美投's 225 / 294 / 380 / 350; terminal value $5.95tn (theirs $5.94tn), PV $3.12tn (exact). The bear gap is
the FCFF path they did not publish.

## Thesis (美投, 2026-10-18) and what moves it

Long term: long-termist DNA (twenty years of losses built e-commerce and AWS; AI needs the same patience)
and the AI industry's upside flowing into the largest cloud. Short term: AWS revenue and margin rising
together on the Anthropic partnership, 2026 capacity release and in-house silicon. Risk: the weakest cash
flow in big tech (FCF negative 2026–27, $366bn of lease/purchase commitments), so a capex raise or higher
rates get punished. Rating Strong Buy, risk level 2, target $350, range $225–$380 ("below 294 undervalued,
225 rational floor, near 380 consider selling"). Eight buy reasons and five sell risks are in
`narrative.py` sections 8–9; the view history (Feb-2024 buy, Dec-2025 cautious long term, Feb-2026 neutral
on the $200bn capex plan, 26Q2 back to positive at $300, 26Q3/Q4 $350) in section 10.

Proven wrong by: AWS growth back under 25% while capex rises, or AWS margin falling two quarters; FY2027
capex guided >10% above the model ($307bn) without backlog growth (美投's own Feb-2026 downgrade trigger).

## Company-specific data

- Segments: North America, International, AWS; revenue and operating income from the press-release
  highlight sentences (`segments.py`). Q4 releases add full-year sentences; the parser takes the first per
  segment. Segment paths beyond FY2026 are display-only extrapolations (own fading growth, trailing margin).
- Guidance wording: "Third Quarter 2026 Guidance • Net sales are expected to be between $197.0 billion and
  $202.0 billion … Operating income is expected to be between $22.5 billion and $26.5 billion"
  (`guidance.py` patterns `revenue_amzn`, `operating_income_amzn`). No capex guidance in the release.
- Balance-sheet mapping: cash + marketable securities; long-term debt + finance-lease liabilities (10-K
  only, carried forward); investments = equity-method + non-marketable equity securities (the Anthropic
  stake; Rivian marks flow through other income). Not used in the valuation in this mode (no bridge).
- Quirks: Q2 2026 pretax income carried ~$53bn of non-operating gains, so reported EPS and trailing P/E are
  inflated; the model sets other income to zero in the forecast. XBRL has no Q4 diluted share count.
  Beta 2-year weekly vs SPY raw 1.48 → adjusted 1.32 (display only; WACC is manual).
- 美投 sources are subscription content: summaries kept in `source/meitou_*.zh.md`, git-ignored.

## What to watch at each print

1. AWS growth and margin versus the "revenue and margin together" thesis; backlog.
2. Operating income against the guided range (the street already assumes a beat); FY2026 margin vs 13.3%.
3. Capex: FY2026 ~$220bn (26.6%); any FY2027 raise above ~$307bn is the bear trigger.
4. After the print: `monitor.py --dir … --apply-actuals`; refresh FY2026–28 from the next 美投 valuation
   update (quarterly) or Bloomberg if available; keep the 2029–31 rows unless the thesis changes; rerun.
5. 美投 cadence: view monthly, valuation quarterly; check jdbinvesting.com/stock/AMZN after each print.

## Log

- 2026-10-22: built on the guidance street (first run bear/base/bull 143/184/224, DCF leg structurally low
  at 26% capex intensity); rebuilt the same day on the 美投 exit-P/E method, reproducing 219/294/384.
- 2026-10-25: `segments.py` removed; atlas segment facts (AWS, North America, International) match the press-release lines: revenue exact, operating income within the $0.1bn rounding of the releases. Guidance from `sec.earnings_guidance` (11 releases, revenue and operating income; the Amazon-specific regexes are deleted). A generic fill on a scratch copy produced a guidance street (147 base vs the keyed 美投 consensus 294): the keyed block stays as the model's street, labelled.
- 2026-10-25: the report's model table now shows the North America / International / AWS rows from the `segments` block (skill fix: the rows were META's); checks name their rule (standard). Monitor rerun: 219 / 294 / 384 unchanged.
