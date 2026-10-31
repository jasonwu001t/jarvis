# MCD — McDonald's playbook

## Status

- Live folder: `~/AlphaResearch/research/MCD/` (`inputs.json`, `narrative.py`, `segments.py`, `source/build_inputs.py`,
  `source/comps_history.py` → `source/comps.csv`, `source/exhibits/` (8-K Ex. 99.1 and 99.2 text since 2019/2022),
  `source/meitou_youtube_mcd_2026-10-25.zh.md`, `MCD_thesis_and_tracking.md`, `reports/`). Full model built 2026-10-24.
- Rebuild order (fill replaces lines): `fill_from_atlas.py --dir research/MCD --since-fy 2022` → `python3 research/MCD/source/build_inputs.py`
  → `monitor.py --dir research/MCD`. The build script repairs the XBRL gaps and keys the street and the judgement; edit it, not inputs.json.
- Calendar fiscal year. Latest reported Q2 2026 (filed 2026-08-07). Next print Q3 2026 on 2026-11-04 pre-market.
- Source: 美投's public YouTube research episode of 2026-10-25 (Chinese; a 美投Pro episode). Rating implied: 观察
  (Watch), small observation position; no target price given. Position: none recorded.

## Thesis and what moves it

US growth has been price-led since 2022 (menu ~40% above 2019 by 2024) with guest counts negative in most quarters
since Q3 2023; Q2 2026 US comps +0.8% with negative traffic while Cava, Starbucks, Texas Roadhouse, Dutch Bros and
Chipotle gained traffic, so MCD lost its "beats peers in any environment" premium. The macro (10-year >5%, Fed hiking,
dividend yield ~3.2% below the risk-free rate) removed the bond-proxy support. The fix (sub-$3 value menu → store
remodel ~$1m/US store → franchisees lack cash → $8.5bn NEXT support through 2036, ~$5bn by 2030, incl. $3–3.5bn rent
relief / remodel subsidies) is necessary but cuts 2027–29 earnings via the rent line (FY2025 rents $10.4bn of
$16.5bn franchised revenue). Buy signal = **US comparable guest counts positive** (the 2003 / 2015 pattern: the stock
outperformed after comps turned). Downgrade = Q3 2026 US comps ≤ −1% with negative traffic, 2027 estimate cuts, rent
relief cutting US franchised margin growth before traffic turns.

## Method and the street

Template method (three-scenario DCF, 12-year convergence, Gordon terminal + P/E on quarters-5-8 **GAAP** EPS, 50/50, rate-aware
multiple at rf_ref 5.0%, ROIC anchor, overlays). No sell-side vendor: the street is McDonald's own 2026 outlook (op margin
mid-to-high 40s, capex $3.7–3.9bn, tax 21–23%, SG&A 2.2% of SWS) and NEXT targets, segment-driven (H2 2026: US +1.5%, IOM +5%,
IDL&C +6% y/y; 2027–28: 2.5% / 4.5% / 6%), US margin 57.5% → 56% as rent relief lands, IDL&C 6%, IOM the residual; other income
−$410m a quarter (net interest); Q4 dividend raised ~5%. Street EPS FY2026 $12.67 (Q3 $3.35 vs Nasdaq $3.37), FY2027 $13.05,
FY2028 $13.88. Adjustments on the **U.S.** segment: bear −2pp, bull +2/+2.5pp (20264–20280); operating margin bear −1pp,
bull +0.5/+1pp (2027–28).

| | Bear (p 30%) | Base (p 45%) | Bull (p 25%) |
|---|---|---|---|
| Story | traffic negative through 2027, rent relief heavier | NEXT delivers slowly, traffic turns H2 2027 | chicken / beverage hit, traffic positive H1 2027 |
| Terminal growth | 3.0% | 3.0% | 3.0% |
| Steady ROIC (realised 2y incremental 20.7%) | 17% | 20% | 23% |
| Steady operating margin (FY2025 46.1%) | 44% | 48% | 52% (company 2030 target) |
| P/E (own 5y fwd range ~17 / 24 / 28, own estimate) | 17x | 22x | 26x |

First run 2026-10-24 ($248.46, 10y 5.00%, adjusted beta 0.53 → WACC 6.4%): bear / base / bull **265 / 334 / 402**, house 334 (+34%),
expected 330; rule "Below bear case"; expected-value exposure 100% → recommended **25%** after the trend overlay (price under the
200-day). Reverse DCF: the price needs −5.3pp a year on the street or a 31% steady margin. Price pays 18.5x quarters-5-8 EPS $13.46.
**The DCF leg is a rate call**: house 334 at beta 0.53, 311 at 0.65, 296 at 0.75, 266 at 1.0; manual WACC 7.5% → 282, 8.0% → 265;
10y 4.5% → 370, 5.5% → 304; g 2.5% → 315. The P/E leg alone is 296 (base). The rules fire "full position" while 美投 says
observation position: the rules are arithmetic, the call is the traffic claim (`us_traffic`, fail until a positive guest-count print).

## Company-specific data

- XBRL gaps repaired in `build_inputs.py`: `shares_diluted` KPI is 0 (use WeightedAverageNumberOfDilutedSharesOutstanding; Q4 =
  4×FY − Q1..Q3), `depreciation_amortization` KPI picks a $0.45bn sub-line (use DepreciationAndAmortization, $2.2bn), no pretax
  concept (pretax = NI + tax; other income = pretax − OI ≈ −$1.6bn net interest), finance-lease additions annual only (spread).
  Working capital = NOPAT + D&A + SBC − (OCF + after-tax interest): without the interest add-back the FCFF is understated by ~$1.2bn a year.
- Segments (`segments.py`): U.S., International Operated Markets, IDL & Corporate (IDL&C + Other revenues) from Ex. 99.2's revenue
  and operating-income tables (2021-Q4 → 2026-Q2 parse; corporate costs sit in IDL&C, Q2 2022 IOM carries the Russia charge).
  Ex. 99.2 files are downloaded by hand into `source/exhibits/<acc>-ex992.txt` (loop in the 2026-10-24 session; add each new one).
- Comps table and the US guest-count sentence are in 8-K Ex. 99.1 (`COMPARABLE SALES`; "U.S.:" bullet); Ex. 99.2
  has franchised sales, restaurant margins by segment, SG&A % of Systemwide sales, operating margin GAAP/non-GAAP,
  the Outlook block, and unit counts by type. `comps_history.py` parses 2021+ tables and 2019–20 sentences; Q4
  releases quote full-year EPS first (handled). XBRL: no `GrossProfit`, `Liabilities`, `SharesOutstanding`; revenue
  in `Revenues`; D&A split across tags; `total_debt` ≈ $40bn; equity negative (buybacks), so no book-value anchors.
- Rent vs royalty split only in the 10-K franchise-arrangements note (FY2025: rents $10,442m, royalties $6,018m,
  initial fees $88m; minimum rents due $3.0bn in 2026).
- Non-GAAP = GAAP less Accelerating the Organization restructuring charges (runs to 2027), ~$0.06/share a quarter.
- Manual / third-party inputs the thesis leans on: sell-side consensus (2027 P/E 17x at $235 ⇒ ~$13.8 EPS implied),
  Black Box industry traffic, NOA and Kalinowski franchisee surveys, value-menu adoption share, peer traffic.
- Dividend $1.86/quarter ($7.44/yr); raise usually declared in October. Treasury par curve for the 10-year.

## What to watch at each print

1. US comps vs the street and the guest-count sentence (sign, and whether check fell to buy traffic).
2. US franchised margin growth vs US franchised sales growth (rent relief leakage from 2027).
3. Operating margin and SG&A % of SWS vs guide; FCF conversion; capex incl. NEXT partnering.
4. Loyalty actives (220m → 250m 2027), unit adds (50,000 in 2028), chicken / beverage launch dates, value-menu adoption.
5. Then: `python3 research/MCD/source/comps_history.py`; re-check the rules in `MCD_thesis_and_tracking.md` §5.

## Log

- 2026-10-24 (later): full model built. `segments.py`, `source/build_inputs.py`, `narrative.py` (5+2, 美投's argument), first monitor run
  (265/334/402, house 334, recommended exposure 25%), thesis tracker with 14 claims (us_growth watch, us_traffic/franchisee/rates/industry
  fail, four pending with due dates 2026-11-04 to 2027-02-10). Not scheduled (owner installs `job ticker-monitor MCD`); not committed.

- 2026-10-24: distilled 美投's YouTube episode (Whisper transcript, no captions), verified every checkable claim
  against the 8-Ks, 10-K, Treasury curve and prices; built the comps extractor (33 quarters, 2018-Q4 → 2026-Q2).
  Full model (inputs.json, narrative, monitor) not built.
- 2026-10-25: the report's model table now shows the U.S. / International Operated Markets / IDL & Corporate rows from the `segments` block (skill fix: the rows were META's); checks name their rule (standard). Monitor rerun: 265 / 334 / 402 unchanged.
