# META — Meta Platforms playbook

## Status

- Live folder: `~/AlphaResearch/research/META/` (`inputs.json`, `narrative.py`, `reports/`, `source/`
  with the 美投 walkthrough transcript and the template's consensus block). README there explains the
  replication and the data map.
- Built 2026-10-20 from 美投估值模板_META_v1.37 (2026-10-15) and its walkthrough video; the engine
  reproduces the workbook to the dollar (bear 610 / base 826 / bull 901 / house 830 at $735).
- Consensus block dated 2026-10-15 (Bloomberg, keyed in). Next print: FY2026 Q3 on 2026-10-21 after
  the close.
- Scheduled: `0 7 * * 1-5 $AR/bin/schedule/job meta-monitor` (AlphaResearch crontab, installed).

## Thesis and the lines it moves

Meta's AI strategy is back on track (Muse), monetisation is unproven but the direction keeps revenue
beating and capex rising; the market pays an above-midpoint multiple for a company beating on both.
Adjustments: Advertising growth +3pp (base) / +5pp (bull) over consensus for FY26 Q3-Q4 and FY2027,
+5pp both in FY2028; capex +5% (base) / +8% (bull) over consensus in FY2027 and FY2028. Bear = consensus
with no premium. Proven wrong by: ad growth at or below consensus two prints running, capex guidance
cut, or Family of Apps margin compressing while capex stays elevated.

## Scenario anchors

| | Bear | Base | Bull |
|---|---|---|---|
| Terminal growth | 3.5% | 3.5% | 3.5% |
| Steady ROIC (own: ~23-24% avg since 2016, 16% in 2022, ~30% now) | 20% | 25% | 30% |
| Steady margin | 35% | 36% | 38% |
| P/E on quarters 5-8 GAAP EPS (own 5y fwd: 14.6 / 18.7 / 22.8) | 18x | 21x | 22x |

House position +5% from base toward bull; 50% DCF / 50% P/E; 12-year convergence; SBC not added back.

## Company-specific data

- Segments: Family of Apps (Advertising + Other revenue) and Reality Labs; revenue and operating
  income by segment from the earnings press-release tables (8-K EX-99.1, URL via
  `sec.earnings_releases`). Not in SEC company-facts.
- Multiple: P/E, GAAP (Meta reports GAAP; Bloomberg's P/E for META is GAAP).
- Balance-sheet mapping that reproduces the template: cash & ST investments = cash + marketable
  securities; debt = long-term debt + finance-lease liabilities (10-K only, carried forward);
  investments = equity-method + non-marketable equity securities (`EquitySecuritiesWithoutReadilyDeterminableFairValueAmount`).
- Quirks: FY2025 Q3 tax charge (EPS 1.05) distorts y/y comparisons; FY2026 Q1 tax benefit.
  Finance-lease additions are annual only in XBRL.
- Beta: 2-year weekly vs SPY raw 1.63 → adjusted 1.42 (Bloomberg 1.43).
- Extra reading when re-underwriting: the transcript in `source/`, `news_search tickers=[META]`,
  `research_filings` for 8-Ks around the print.

## What to watch at each print

1. Advertising revenue growth versus consensus (+3 to +5pp is the thesis); FY26 Q3E model 63,284 vs
   consensus 61,781.
2. Capex and the capex guidance range versus consensus (+5 to +8%); FY2027E base capex $207bn.
3. Operating margin (model 31% Q3E, 34% Q4E) and Family of Apps margin (39% / 43%).
4. After the print: `monitor.py --dir … --apply-actuals`, key in segments, refresh consensus.

## Backtest (2026-10-21, `research/META/backtest/`)

Decision at each earnings release + 2 trading days, Oct 2023 → Oct 2026, today's assumptions and
rules. Growth of $1: momentum street / rules 2.12x; guidance street / rules 2.11x; guidance / EV sizing
with the rate-aware multiple and ROIC anchor 1.87x; all improvements with the overlays 1.75x; foresight
street 2.63x; buy-and-hold 2.34x; SPY 1.87x. Max drawdown 34% for every variant except guidance/rules
(30%). Readings:

- Guidance fixed the late-2023 miss (house target 446 instead of 293 at $297) because Meta's own range,
  beat-adjusted, saw the inflection the trailing numbers could not. Meta guides conservatively: the
  beat against its midpoint runs ~1.04-1.06; the street uses that factor.
- Expected-value sizing and the overlays cost return in this window: a one-name bull market with no
  regime stress, where every reduction from full exposure was a drag and the 35% vol target scaled a
  46%-vol stock to ~0.75. They are insurance; they pay in a drawdown this window does not contain.
- Targets were well-calibrated: 12-month price inside the bear–bull band 4-6 of 8 times; house target
  error 15-16% with the guidance street versus 23% with momentum.

Lesson: the method's edge is the forecast block (consensus and guidance) and the thesis uplift, not the
mechanics. Keep the consensus fresh; treat the overlays as a risk budget, not a return engine; do not
tune thresholds on this sample.

## Log

- 2026-10-20: built; live run at $694 gave bear 598 / base 808 / bull 881 / house 812 (+16.9%), rule
  "Hold zone"; terminal value 81% of EV flagged (template's own warning). HTML report and cron job added.
