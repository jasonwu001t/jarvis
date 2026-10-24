# AMD — Advanced Micro Devices playbook

## Status

- Live folder: `~/AlphaResearch/research/AMD/` (`inputs.json`, `narrative.py`, `segments.py`, `source/exhibits/`,
  `source/edgar/` (deal and financing 8-K exhibits), `reports/`). Calendar fiscal year; latest reported Q2 2026
  (quarter ended 2026-06-27). Next print: Q3 2026 on 2026-11-03.
- Built 2026-10-23 as a **house view** (美投 does not cover AMD) in the 5+2 structure, from AMD's SEC filings and the
  competitive frame in 美投's NVDA / INTC / TSM / AVGO / MU research.
- Scheduled: none. Position: none recorded.

## Method and the street

Template method (three-scenario DCF with 12-year convergence + P/E on quarters-5-8 **adjusted** EPS, 50/50,
rate-aware multiple, ROIC anchor, overlays). `earnings_basis "adjusted"`: adjustments = amortisation of acquisition
intangibles after tax (not SBC), so adjusted EPS sits between GAAP and the street's non-GAAP.

- **No sell-side consensus is loaded** (official sources only). The consensus block is: Q3 2026 at the company's
  $13.0bn ± $0.3bn guide (8-K 2026-08-04, ~56% non-GAAP gross margin), Q4 +10% sequential, then AMD's Financial
  Analyst Day (2025-11-11) long-term model: revenue CAGR >35%, data centre >60%, non-GAAP operating margin >35%,
  EPS >$20 in 3–5 years, translated to GAAP operating margin 22% (FY2027) and 27% (FY2028). Tax 14%, capex 4.5%,
  D&A 5% → 4.5% of revenue. Segment paths: Data Center 60% then 55% growth at 30–35% margin; Embedded recovery;
  Client & Gaming the residual.
- Scenarios (judgement 2026-10-23): bear growth −12pp, margin −4pp, steady margin 20%, ROIC 18%, 24x; base = the
  company model, steady 26% / 25%, 30x; bull growth +8pp, margin +3pp, steady 30% / 30%, 36x. Probabilities 25/50/25.
- Share count = today's diluted 1.66bn; the 320m warrant shares (OpenAI, Meta) and the ~$8.2bn World Labs stock are
  **not** in the count, which flatters the bull case by up to ~19%.

First run (2026-10-23, price $507.93, beta 1.57, WACC 11.5%): bear / base / bull **196 / 408 / 674**, house 408
(Hold; rule "Stretched"); expected value 422; reverse DCF needs +5.6pp a year over the 35% model or a 28% steady
margin. Price pays 45x base-case adjusted quarters-5-8 EPS ($11.26).

## Thesis and what moves it

The second source for AI compute in a market Nvidia owns (美投: 85% share, AMD 5–8%) that grows 30%+ a year; CPU
share gains in a volume-and-price upcycle (美投's INTC view); execution under Lisa Su; anchor supply agreements with
OpenAI (Product Purchase Agreement 2025-10-05, 160m-share warrant at $0.01) and Meta (Master Purchase Agreement
Amendment Eight 2026-02-23, 160m-share warrant). Risks: Nvidia's Rubin cadence and supply lock-up, custom ASICs
(Broadcom/Marvell for Google, Meta, OpenAI, Anthropic), dilution, export controls (MI308), HBM/CoWoS supply, price.

Proven wrong (upgrade) by: price near the base value with the ramp intact, or Data Center above the $46.5bn FY2027
path for two quarters at >33% segment margin. Downgrade by: MI400 shipments slipping past Q1 2027, a Q4 guide under
+10% sequential, gross margin below the 56% guide.

## Company-specific data

- `segments.py`: parses the 2025+ release table ("Net Revenue: Data Center Segment … Operating Income (Loss) …")
  into Data Center, Client and Gaming (Client + Gaming), Embedded with segment operating income; older releases
  fall back to sentence matching. Applied by hand to the cached exhibits (the fill's segment hook also works).
- D&A: XBRL `Depreciation` (FY) + `AmortizationOfIntangibleAssets` (YTD, de-cumulated); FY2024 amortisation keyed
  at ~$2.4bn. Working capital recomputed as NOPAT + D&A + SBC − OCF after D&A is in.
- Guidance wording: "For the third quarter of 2026, AMD expects revenue to be approximately $13 billion, plus or minus
  $300 million … Non-GAAP gross margin is expected to be approximately 56%." No `guidance.py` pattern yet; keyed by
  hand.
- Filings worth re-reading each quarter: warrant vesting disclosures (OpenAI/Meta), the $4.75bn notes (2026-08-17),
  World Labs closing (2026-09-28), ZT Systems/Sanmina partnership (2025-10-27).

## What to watch at each print

1. Data Center revenue and segment margin (Q2 2026: $6.7bn, 31%); Instinct vs EPYC colour; MI400/Helios timing.
2. Gross margin vs the 56% guide; inventory build ahead of the ramp.
3. Warrant vesting (dilution), export-licence status, HBM/CoWoS commentary.
4. After the print: `monitor.py --dir … --apply-actuals`; key the new quarter's guide; refresh the long-term model
   if AMD updates it; rerun.

## Log

- 2026-10-23: quick model (guidance street: 155/274/457), then full build on the company's long-term model
  (196/408/674) with narrative and segments.
