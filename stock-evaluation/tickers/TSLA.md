# TSLA — Tesla playbook

## Status

- Live folder: `~/AlphaResearch/research/TSLA/` (`inputs.json`, `narrative.py`, `source/meitou_*.zh.md` (local only),
  `reports/`). Calendar fiscal year; latest reported Q2 2026. Next print: Q3 2026 in late October.
- Built 2026-10-23 on the 美投 (jdbinvesting.com) TSLA method: sum-of-the-parts valuation video 2026-08-17 (37 min),
  5+2 (2026-09-28 refresh of 2026-05-22), Q2 research 2026-07-25, view update 2026-09-22.
- Data: XBRL under TSLA works for consolidated history. **The forecast lines are the car business only** (美投's
  volume × price path); energy, FSD, Robotaxi and Optimus are `blend.sotp_addons`. The report's revenue/FCFF charts
  step down at the join (consolidated history → automotive forecast); the P/E leg and "P/E the price pays" are
  meaningless here (0% weight).
- Scheduled: none. Position: none recorded.

## The method (美投 TSLA, reproduced by the engine)

Sum of the parts, new engine feature `blend.sotp_addons` (see `references/valuation-method.md`):
- **Car business DCF**: `terminal_mode "exit_pe"` 15x on 2030 net income, `wacc.mode manual` 0.074 (Ford/GM
  average), `valuation_date "fy_end"`, no bridge, no roll-forward, `shares_override 3950`. Path: 1.69m vehicles
  2026 → 2.65m 2030 (~10% CAGR), $41.5k then −1%/yr, gross margin 18.5% → 19%, operating income 30% → 55% of gross
  profit, capex $25bn (2026–28) / $22bn / $21bn (all Tesla capex), D&A $6.5–14bn, tax 15%. H2 2026 = car-revenue
  residual (H1 automotive ≈ 78% of consolidated). Scenarios as growth/margin adjustments: bull +4.8pp growth and
  +1pp margin (3.3m, GM 20.5%), bear −5.5pp and −0.6pp (2.1m).
- **Add-ons** at 15.2% (Bloomberg/FactSet average), end-2030 values converted from 美投's per-share results:
  FSD 29.4 / 44.7 / 71.6 (2030 revenue $15.5bn = fleet × 50% penetration × $150/month, 20x P/S); Robotaxi
  124 / 201 / 289 (600k cars × 18h × 60–65% × 22 mph × $2.2/mile, 8x P/S; bull 800k & 70%, bear 400k & 60%);
  Optimus 8 (30k robots × $84k × 20x); Energy 14.8 (~$35bn × 3x). 美投's revenue × multiple arithmetic in the
  transcript has typos; the per-share figures are authoritative.
- `target_position 1.0`: 美投 set its $421 target at the bull case. Probabilities 25/50/25; EV sizing and overlays on.

Reproduction (2026-10-23, price $374.58): bear / base / bull **191 / 290 / 415**, house 415; 美投 203 / 289 / 421,
target 421. Their bear does not sum from their parts (energy mis-keyed at 32.2; the parts give ~186).

## Thesis (美投, 2026-09-22) and what moves it

The only listed physical-AI pure play (FSD → Robotaxi → Optimus); FSD penetration <10% of a huge fleet; Robotaxi
reprices a trillion-dollar mobility market (ride-hailing 1% penetrated); Optimus the biggest option. Near term:
fundamentals floored (oil, energy), FSD approvals in 7 EU countries (EU vote Oct 6; China pending), Cybercab in
Austin; but capex $25bn+, FCF negative, every milestone (V15, fleet scale, Optimus) pushed to 2027: no catalyst.
Rating 积极/BUY (cut from 非常积极), risk 3, target $421 (bull), range $203–$421 (26Q2 213/333/450, 26Q1
241/370/498, 25Q4 266/377/538). Risks: Musk's focus (strong), policy limits incl. NHTSA's 21 Cybercab questions
(strong), capex/FCF (strong), Robotaxi delay if V15 slips (strong), competition (weak).

Proven wrong by: EU vote failing or China not approving by year-end; V15 slipping into 2027 or unsupervised miles
not compounding; 2026 capex above $30bn without milestones; Q3 deliveries below 435k; a formal shift of Musk's time.

## What to watch at each print

1. FSD subscribers (1.48m), attach rate on new cars (55%), penetration (15.3%), Europe/China approvals.
2. Robotaxi paid miles (2.5m) and unsupervised miles (380k, double-digit weekly growth), cities, Cybercab data.
3. Deliveries vs 1.69m for 2026; automotive gross margin ex-credits (16.3%); capex and the $30bn debt plan.
4. After the print: `monitor.py --dir … --apply-actuals` (history), then re-key the car path and the add-on values
   from the next 美投 valuation update (quarterly); rerun.

## Log

- 2026-10-23: built on the 美投 sum-of-the-parts method (engine gained `sotp_addons`), reproducing 191/290/415;
  narrative from four 美投 pieces.
