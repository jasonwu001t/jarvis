# The report (`reports/<date>.html`, copied to `reports/latest.html`)

The deliverable a reader makes the call from. One page, sticky section nav, light and dark mode,
print styles; tables scroll horizontally with a sticky label column; actual / consensus-plus-house /
model-year columns are colour-coded and annual columns bold. Charts are Plotly (CDN).

## Sections, in order, and why

1. **The call.** A verdict paragraph: where the price sits between bear, base and bull; what you are
   paid if the house view plays out and lose if the company merely meets consensus; the multiple the
   price pays against the company's own range; the house target, upside and the rule in force. Six
   tiles (house target, upside, the three scenario values, price-implied multiple, WACC, base revenue
   CAGR). "What to watch at the next print", generated from the adjusted lines. Then the **scenario
   matrix**: what you must believe (adjustments and steady-state assumptions per scenario) and what
   you get (CAGR, EPS, DCF, P/E, blended, upside), with the baseline for drift.
   *Why first:* the reader should be able to stop after one screen.
2. **The argument.** The company-specific narrative from the ticker folder's `narrative.py`, every
   number recomputed live; the FCFF, P/E-range and targets charts sit inside it. Without a
   `narrative.py` the report renders a four-step generic method walkthrough.
3. **Financial model.** Every row of the forecast sheet (income statement with segments, cash flow,
   balance sheet, non-GAAP and ROIC) for the actual and explicit periods, then the transition years,
   under a bear / base / bull toggle.
4. **Valuation.** The shared WACC table; for the selected scenario the discounted-cash-flow table,
   the bridge (EV → equity → per share → 12 months forward → target), the P/E leg and the blend.
5. **Sensitivities.** Base DCF on steady ROIC × margin; P/E target on multiple × scenario EPS; the
   risk-free rate. *Why:* these are the judgement calls; the reader must see what each is worth.
6. **Assumptions and adjustments.** Settings, scenario parameters, the adjustment table, the house
   view paragraph (`thesis.summary`) and rating.
7. **Monitor.** Position rules (fired ones highlighted), live inputs with their dates, the check
   list, newly filed quarters with actual-versus-consensus and the roll instruction, the manual items.
8. **Sources and method notes.**

## UX rules

- Lead with the decision; mechanics after. Numbers that drive the call appear with their date.
- One idea per tile; bold only the value. No dual-axis charts; one hue per series, fixed order
  (blue DCF/base, green P/E/bull, orange bear/price); the price is always a dotted orange line.
- Negative values in red in tables; dashes for genuinely absent data, never zeros.
- Manual inputs are named as manual in three places: the subtitle (consensus date), the monitor
  block, the sources. Baseline values sit beside live ones so a reader sees drift, not surprise.
- The markdown twin (`reports/<date>.md`) is the short monitor for terminals and chat.
