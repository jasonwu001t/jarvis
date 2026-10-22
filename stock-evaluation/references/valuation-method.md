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

## Equity bridge and DCF target

Equity = EV − net debt (interest-bearing debt incl. finance leases − cash and marketable securities)
− minorities + investments (equity-method + non-marketable). Per diluted share (latest quarter),
× (1 + cost of equity) to roll 12 months forward, − the next four quarters' dividends per share.

## WACC

Cost of equity = risk-free + beta × ERP. After-tax cost of debt = pretax cost × (1 − TTM effective
tax rate over the last four quarters). Weights: market cap (price × diluted shares, or the override)
versus debt. Beta is Bloomberg-style: 2-year weekly raw beta vs SPY, adjusted 0.67 × raw + 0.33.

## The multiple leg

Quarters 5-8 after the balance-sheet date: `w = (4 − reported quarters)/4`;
`NI = w × NI(FY+1) + (1 − w) × NI(FY+2)` (GAAP or adjusted per `blend.earnings_basis`), shares
likewise; target = multiple × NI / shares. P/E only in this version (`blend.multiple_type`); for
EV/EBITDA, P/S or P/B extend `multiples()` the way the template's 估值 sheet does.

## Blend and house target

Scenario value = `dcf_weight × DCF + (1 − dcf_weight) × multiple`. House target =
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
transition year (warning); starting reinvestment ratio > 0 and ≥ steady state (warning).

## What is judgement

The adjustments, the steady-state ROIC / margin / tax, the multiple, the convergence length and
shape, the SBC treatment, the ERP. Everything else is data. The report's sensitivity grids show what
each judgement is worth; make the user look at them.
