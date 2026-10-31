# The valuation method (what `scripts/valuation_engine.py` computes)

A re-implementation of the 美投估值模板 (Meitou valuation template) v1.37, verified against its META
workbook to the dollar. Units: USD millions unless per share; rates as fractions. Period keys are
`year*10 + quarter` (quarter 0 = fiscal year): 20263 = FY2026 Q3, 20270 = FY2027.

## Timeline

- **Actuals** through the latest filed quarter (`as_of.latest_reported_fy/q`, `balance_sheet_date`).
- **Explicit period**: the unreported quarters of the current fiscal year plus FY+1 and FY+2, from
  sell-side consensus with the house adjustments layered on.
- **Transition**: FY+3 … FY+2+N (N = `blend.convergence_years`, 12 in the template), every driver
  gliding linearly to the steady state.
- **Perpetual** after that: terminal growth and steady-state ROIC.

**Exit-multiple variant (美投's AMZN method, `blend.terminal_mode: "exit_pe"`).** Consensus annual
periods beyond FY+2 (status `consensus`, q 0) extend the explicit period; the last of them is the
terminal year. `blend.convergence_years: 0` removes the transition entirely, so the timeline is
actuals → explicit years → terminal value. The report's sensitivity grids switch to exit P/E × WACC
and capex × margin-path when this mode is on.

## Adjustments (the house view)

An adjustment is `(line, period, pp per scenario)`: percentage points added to consensus growth of a
business line (a segment), of total revenue, of operating margin, or of capex.

- Quarter q: `Δ = consensus(same quarter last year) × pp`.
- FY+1: `Δ = Δ(FY) × cons(FY+1)/cons(FY) + (cons(FY) + Δ(FY)) × pp`, where `Δ(FY)` is the sum of the
  quarterly deltas; FY+2 repeats the recursion from FY+1.
- A line's Δ rolls up to its parent segment and to total revenue.
- `Δ operating income = Δ revenue × consensus operating margin of the parent segment` (a loss-making
  segment's margin is floored at 0), plus any explicit margin adjustment.
- Capex: quarter `cons + same quarter last year × pp`; FY+1 `cons(FY+1) + Δcapex(FY) × cons(FY+1)/cons(FY)
  + (cons(FY) + Δcapex(FY)) × pp`; FY+2 likewise.

## Per-period P&L and cash flow (explicit period)

Pretax = operating income + consensus other income. Tax at the consensus effective rate, falling
back to the steady-state rate when pretax ≤ 0 or the rate is outside 0-50%. Net income; EPS on
consensus diluted shares; dividends scale with net income relative to consensus.
`NOPAT = operating income × (1 − tax)`.
`FCFF = NOPAT + D&A − capex − finance-lease additions − working-capital increase`.
Stock-based compensation stays expensed (not added back): the conservative convention.

## Transition years

With FY+2 as the start and the scenario's steady state as the end, for step k of N:
growth, operating margin, tax rate and the net-reinvestment ratio move linearly;
`reinvestment ratio = (capex + leases − D&A + ΔWC) / revenue`, steady state
`g / ROIC × margin × (1 − tax)`. D&A keeps its FY+2 ratio to revenue; ΔWC keeps its FY+2 ratio to
incremental revenue; finance leases keep their FY+2 share of capex.

## Terminal value and discounting

`TV = NOPAT(last year + 1) × (1 − g/ROIC) / (WACC − g)`, discounted from half a year before the end of
the last transition year. Cash flows are discounted mid-year from the balance-sheet date; the current
year's stub (unreported quarters only) to the midpoint of the remaining half year.

**Exit P/E** (`terminal_mode: "exit_pe"`): `TV = net income(last explicit year) × scenarios.<k>.exit_pe`,
discounted from the end of that year; no transition years and no Gordon formula. `blend.valuation_date:
"fy_end"` restates every present value at the current fiscal year end instead of the balance-sheet date
(美投 states "fair value at end-2026"); the default `"balance_sheet"` keeps the template convention.

**Sum-of-the-parts add-ons** (`blend.sotp_addons`, 美投's TSLA method): a list of businesses valued outside the
DCF, each `{name, year, discount_rate, terminal_value (number or {bear, base, bull}), basis}`. The engine
discounts `terminal_value` from the end of `year` to the valuation date at `discount_rate` and adds it per
share to the DCF value; `dcf["core_per_share"]` keeps the DCF-only figure and `dcf["addons"]` the parts. The
DCF lines then model only the core business (TSLA: cars), with the history consolidated.

## Equity bridge and DCF target

Equity = EV − net debt (interest-bearing debt incl. finance leases − cash and marketable securities)
− minorities + investments (equity-method + non-marketable). Per diluted share (latest quarter),
× (1 + cost of equity) to roll 12 months forward, − the next four quarters' dividends per share.
`blend.equity_bridge: false` skips the bridge (equity = DCF total), `blend.dcf_roll_forward: false`
skips the roll-forward, `market.shares_override` replaces the diluted count: the three switches the
美投 AMZN method uses (DCF total / 10,783m shares, stated at end-2026, no bridge).

## WACC

Cost of equity = risk-free + beta × ERP. After-tax cost of debt = pretax cost × (1 − TTM effective
tax rate over the last four quarters). With no stated pretax cost (`wacc.pretax_cost_of_debt` null: a fresh
fill, a filer without debt) the engine uses risk-free + `wacc.debt_spread` (default 1.5%) and the report,
the markdown and the summary carry a WARNING saying so. Weights: market cap (price × diluted shares, or the override)
versus debt. Beta is Bloomberg-style: 2-year weekly raw beta vs SPY, adjusted 0.67 × raw + 0.33.
`wacc.mode: "manual"` with `wacc.value` overrides the computed WACC (美投 AMZN: the average of
Bloomberg's and FactSet's, 13.8%); the CAPM cost of equity is still computed for display and the
roll-forward, and the report's rate sensitivity steps the manual WACC instead of the risk-free rate.

## The multiple leg

Quarters 5-8 after the balance-sheet date: `w = (4 − reported quarters)/4`;
`NI = w × NI(FY+1) + (1 − w) × NI(FY+2)` (GAAP or adjusted per `blend.earnings_basis`), shares
likewise; target = multiple × NI / shares. P/E only in this version (`blend.multiple_type`); for
EV/EBITDA, P/S or P/B extend `multiples()` the way the template's 估值 sheet does.

A negative or near-zero earnings base (quarters 5-8 net income at or below `blend.pe_min_net_margin`, default
1%, of quarters 5-8 revenue) has no meaningful multiple: that scenario's P/E leg is off (`multiples.target`
None, `disabled` true, the raw figure kept as `raw_target`), its weight moves to the DCF, and a WARNING names
the scenario. A loss-maker valued on GAAP therefore never gets a negative target from the P/E leg; switch
`earnings_basis` to adjusted when a non-GAAP bridge exists (CRWD) rather than live with a DCF-only value.

## Blend and house target

Scenario value = `dcf_weight × DCF + (1 − dcf_weight) × multiple` (the DCF alone when the P/E leg is off). House target =
`base + p × (bull − base)` for p ≥ 0, `base + p × (base − bear)` for p < 0 (`blend.target_position`).

## Rate-aware multiple (`blend.multiple_rate_aware`)

A target multiple set when the 10-year was `rf_ref` is applied as `m × (rf_ref + ERP) / (rf + ERP)`,
so the P/E leg does not silently drift as rates move. The stated multiple is kept for display.

## Probability-weighted value and sizing (`scenarios.<k>.probability`, `blend.sizing`)

Expected target = Σ p × blended scenario value. Reward to risk = (expected − price) / (price − bear
value), infinite when the bear value is above the price. Exposure = `neutral + (1 − neutral) × rr /
full_at_reward_to_risk`, clipped to 0..1: the neutral weight at fair value, full at the reward-to-risk
threshold, zero when the bear value is that far below. This replaces "house = 5% toward bull" as the
position signal; the house target is still reported.

## Reverse DCF (`out["implied"]`)

What the price assumes in the base scenario, each solved by bisection: percentage points added to
consensus growth in every forecast period (house adjustments kept) so the blended target equals the
price; the steady-state margin at which the base DCF equals the price; the steady-state ROIC likewise.
Far less sensitive to terminal assumptions than the target itself; monitor it quarter by quarter.

## Realised incremental ROIC and the anchor (`out["returns"]`, `blend.steady_roic_anchor`)

ΔNOPAT (TTM now versus TTM `years` ago) over the net reinvestment of those years (capex + leases − D&A
+ ΔWC), reported quarters only. With the anchor enabled the base steady-state ROIC is pulled down to
it when it is lower (floored at WACC + `floor_over_wacc`), and bear and bull shift by the same amount;
a check warns whenever realised sits below the assumed steady state.

## Checks (fail = an input is wrong)

WACC > g; steady ROIC ≥ WACC; bear ≤ base ≤ bull; terminal value ≤ 80% of EV (warning); base
multiple inside the own 5-year range (warning); implied return on new investment ≥ WACC in every
transition year (warning); starting reinvestment ratio > 0 and ≥ steady state (warning); realised
incremental ROIC ≥ the base steady ROIC (warning).

The ROIC and reinvestment checks take the company type into account and each says which rule it used
(`company.business_model`, or detected from the reported fiscal years: cyclical when revenue fell 15% or
more in a year, deferred revenue when the median working-capital build is below −1% of revenue):

| Check | standard rule | cyclical rule | deferred-revenue rule |
|---|---|---|---|
| Steady ROIC ≥ WACC (fail) | every scenario | the probability-weighted average across scenarios (a bear trough below WACC is the cycle) | standard |
| Realised ROIC ≥ base steady ROIC (warning) | 2-year incremental ROIC | through-cycle average of annual ROIC (NOPAT / (equity + net debt)) over the reported years | 2-year incremental ROIC with a working-capital release counted as zero |
| Implied return on new investment ≥ WACC (warning) | every transition year | the whole transition at the steady (mid-cycle) margin: revenue added × steady margin after tax / cumulative reinvestment (equals steady ROIC in a steady state) | standard |
| Starting reinvestment > 0 and ≥ steady state (warning) | (capex + leases − D&A + ΔWC) / revenue | standard | negative working capital not counted against it |

A company can be both (cyclical rules for ROIC, deferred-revenue rule for reinvestment). Declare
`business_model: "standard"` to switch detection off.

## What is judgement

The adjustments, the steady-state ROIC / margin / tax, the multiple, the convergence length and
shape, the SBC treatment, the ERP. Everything else is data. The report's sensitivity grids show what
each judgement is worth; make the user look at them.
