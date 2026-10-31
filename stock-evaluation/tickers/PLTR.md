# PLTR — Palantir playbook

## Status

- Live folder: `~/AlphaResearch/research/PLTR/` (`inputs.json`, `narrative.py`, `source/meitou_*.zh.md` (local only),
  `reports/`). Calendar fiscal year; latest reported Q2 2026. Next print: Q3 2026 in early November.
- Built 2026-10-23 on the 美投 (jdbinvesting.com) PLTR method: valuation video 2026-08-20, 5+2 2026-08-30, Q2 research
  2026-08-08, FDE research 2026-07-29, view update 2026-10-19.
- Data: XBRL under PLTR works; Palantir has no interest-bearing debt (the filler now carries 0 when a balance line has
  no recent value). No segment split in XBRL; the forecast carries `seg:Government` / `seg:Commercial` from 美投's
  paths (display only; actual split assumed 51/49 for FY2025).
- Scheduled: none. Position: none recorded.

## The method (美投 PLTR, reproduced by the engine)

Exit-P/E variant with a twist: **consensus is the bear case** (Palantir beats and raises every quarter), base and bull
are uplifts. `terminal_mode "exit_pe"`, `convergence_years 0`, `valuation_date "fy_end"`, `equity_bridge false`,
`dcf_roll_forward false`, `dcf_weight 1.0`, `wacc.mode "manual"` 0.1754, `market.shares_override 2403`,
`target_position 0.0` (美投's $191 = base).

- Five explicit years FY2026–30 on two segments. Bear/consensus: government +65/35.7/36.4% then 30%; commercial
  +96/61% then ~47% (2028 not stated); adjusted operating margin ~58% (2026–28) then 53%; tax 19%, other income
  $0.4bn, capex 0.8%, D&A 0.5% of revenue. 2030 bear net income ≈ $14.8bn (theirs $14.6bn).
- Base: total-revenue growth +3pp every year (gov +3pp, commercial ~+3pp), margin +1pp (54% in 2030), exit P/E
  50x. Bull: +7.5pp (commercial to ~$30bn in 2030), margin +1pp through 2028 and +2pp in 2029–30 (55%), 55x.
  Bear exit 45x (Netflix precedent). WACC 17.54% = average of Bloomberg 22.2% and FactSet 12.87%.
- Probabilities 25/50/25; EV sizing and overlays on. Margins are 美投's adjusted basis (SBC excluded), so the
  model's forecast FCFF is before stock compensation.

Reproduction (2026-10-23, price $196.19): bear / base / bull **157 / 193 / 245**, house 193; 美投 155 / 191 / 248,
target 191.

## Thesis (美投, 2026-10-19) and what moves it

Positive: AI data-analytics market is huge, non-tech AI adoption still low, existing customers renew and expand (NDR
157%, 74% of growth from the installed base), US commercial can keep accelerating (full-year guide 150%), software
has priced in the disruption scare. Negative: the growth peak is postponed to 2027, not cancelled; the stock is in
"find the floor on growth (50% or 30%?), find the anchor on valuation" with high volatility. Rating 积极 (cut from
非常积极 in 26Q3), risk 3, target $191, range $155–$248 (26Q2 130/188/244, 26Q1 125/182/236). Risks: midterms
hitting government orders (strong), ontology bypassed by agents (weak), FDE talent war (weak), post-peak valuation
uncertainty (weak).

Proven wrong by: US-commercial TCV or 12-month RPO growth slowing two quarters; NDR below ~140% without net customer
adds turning up; US commercial growth below 100% with FDE headcount stalling; a Congress change or US-government
growth below 50%.

## What to watch at each print

1. US commercial TCV (record $2.13bn in Q2), RDV, RPO (12-month portion growth), NDR (157%), deal-size mix
   (>$10m deals 73).
2. US commercial revenue growth (150% guide) and customer adds (653) alongside FDE headcount commentary.
3. US government growth (90%) into the midterms; international.
4. After the print: `monitor.py --dir … --apply-actuals`; refresh the segment paths from the next 美投 valuation
   update (quarterly) or Bloomberg; keep 2029–30 unless the thesis changes; rerun.

## Log

- 2026-10-23: built on the 美投 consensus-as-bear exit-P/E method, reproducing 157/193/245; narrative from five
  美投 pieces.
- 2026-10-25: the report's model table shows the Government / Commercial rows from the `segments` block; the checks use the deferred-revenue rule (detected: median working-capital build -2.4% of revenue); the starting-reinvestment check still warns (capex less D&A 0.3% of revenue against the 4.5-5.4% the steady ROIC needs). Monitor rerun: 157 / 193 / 245 unchanged.
