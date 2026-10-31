# NVDA — NVIDIA playbook

## Status

- Live folder: `~/AlphaResearch/research/NVDA/` (`inputs.json`, `narrative.py`, `source/meitou_*.zh.md` (local only),
  `reports/`). Fiscal year ends January (`fiscal_year_end_month: 1`): FY2027 = the year to January 2027, which 美投
  calls "2026". Latest reported FY2027 Q2 (quarter ended 2026-07-26).
- Built 2026-10-23 on the 美投 (jdbinvesting.com) NVDA method: valuation video 2026-09-01, 5+2 walk-through
  2026-10-19, FY27Q2 earnings research 2026-08-29, view update 2026-10-17. Next print: FY2027 Q3 on 2026-11-18.
- No `segments.py` (data centre / gaming / pro-vis / auto are in press-release tables; 美投's hyperscaler vs ACIE
  split comes from the call). Nvidia guides one quarter ahead in the release ("revenue is expected to be
  $108.0 billion, plus or minus 2%"): `guidance.py` has no pattern for it yet, so Q3 is keyed by hand.
- Scheduled: none. Position: none recorded.

## The method (美投 NVDA, reproduced by the engine)

Exit-P/E variant: `terminal_mode "exit_pe"`, `convergence_years 0`, `valuation_date "fy_end"` (January 2027),
`equity_bridge false`, `dcf_roll_forward false`, `dcf_weight 1.0`, `wacc.mode "manual"` 0.17,
`market.shares_override 24100`, `target_position 0.0` (美投's $295 target is its base case).

- Five explicit years FY2027–FY2031. FY2027–29 = Bloomberg as quoted (growth 88.8/65.4/29.3%, operating margin
  65.6/66.1/66.7%); FY2030–31 = 美投 (growth 15/10%, margin 66%). FY2027 Q3 = the $108bn outlook, Q4 the residual.
  Tax 16%, other income 0.8% of revenue, capex 2.5%, D&A 1.2%, working capital 32% of incremental revenue (set
  high to approach 美投's $1.23tn PV of FY2027–31 FCFF; the model still lands ~$1.37tn).
- Terminal = FY2031 net income × 18x (cut from 20x for circular-financing leverage; bull 20x, bear 16x), WACC 17%
  (Bloomberg/FactSet average, up from 14.8% in June), / 24.1bn shares, no bridge.
- Bull/bear exactly as the video: growth +10pp FY2027–29 and +5pp FY2030–31 / −5pp every year; margin ±2pp every
  year. Probabilities 25/50/25; EV sizing and overlays on.

Reproduction (2026-10-23, price $212.21): bear / base / bull **227 / 303 / 433**, house 303; 美投 217 / 295 / 432,
target 295. TV $11.1tn (theirs ~$11tn), PV TV $5.94tn (theirs $5.9tn); the base gap (~3%) is the FCFF PV.

## Thesis (美投, 2026-10-17) and what moves it

Two long-term reasons: long visibility of compute demand (the compute base layer; whatever wins, demand converges
on Nvidia) and an all-round moat (CUDA, interconnect, delivery reliability, supply-chain power, distributed
inference, cost per token). Short term: Rubin ramping (20% of data-centre revenue next quarter) and ACIE
(sovereigns/neoclouds/enterprises) outgrowing hyperscalers. Risks: AI monetisation and compute spending
(strong), memory squeezing GPU budgets 2027–28 (strong), custom silicon and AMD (strong), hyperscaler capex
slowing (strong), circular financing lowering revenue quality (key), CoreWeave (weak), margin compression (weak).
Rating 非常积极 (upgraded 26Q3), risk 2, target $295, range $217–$432 (26Q2 193/261/349, 26Q1 161/220/296, 25Q4
149/191/235).

Proven wrong by: Rubin below 20% of data-centre revenue next quarter or the FY2028 guide cut below +70%; gross
margin trough below 71% or no recovery to 72–73%; hyperscaler 2027 capex guided below $1.1tn; supported-lab
revenue above a quarter of the total or a backed customer failing.

## Company-specific data

- XBRL under NVDA works (D&A, capex present); XBRL has no Q2 diluted count in some quarters (filled from Q1).
- Other income: FY2027 Q1 carried $16bn of non-operating gains (investment marks); the forecast uses 0.8% of
  revenue. Balance sheet: cash $57bn, debt $8.5bn, investments small; not used (no bridge).
- Beta ≈ 1.57 adjusted (display only). Reference P/E: forward ~17x (Sep 2026), 25x in 2024–25, 33x a year ago;
  美投's fair range after the circular-financing discount 20–22x; exit 18x.
- Credit exposure (customer guarantees/funding): Morgan Stanley ~$200bn by end-2028 vs ~$350bn net cash; a
  quarter of FY2028 revenue from labs Nvidia supports (management). Track as a thesis line.

## What to watch at each print

1. Rubin share of data-centre revenue (20% guided next quarter) and the FY2028 +70–100% guide.
2. Gross-margin path (74% → 71–72% trough → 72–73%); supplier purchase commitments ($279bn) as the memory lock.
3. Hyperscaler vs ACIE mix (55/45) and ACIE growth; hyperscaler capex guides ($800bn 2026, $1.3tn 2027).
4. Circular financing: supported-customer revenue share, CoreWeave and other backed neoclouds.
5. After the print: `monitor.py --dir … --apply-actuals`; key in the next-quarter outlook; refresh FY2027–29 from
   the next 美投 valuation update (quarterly) or Bloomberg; keep FY2030–31 unless the thesis changes; rerun.

## Log

- 2026-10-23: built on the 美投 exit-P/E method, reproducing 227/303/433; narrative from four 美投 pieces.
- 2026-10-25: first claims board: `consensus_revision` (consensus 2.47 → 2.49 for 2026-11-18).
