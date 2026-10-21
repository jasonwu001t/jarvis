# <TICKER> — <Company> playbook

_Copy to `tickers/<TICKER>.md`. Keep it short and current: it is what the next evaluation reads first._

## Status

- Live folder: `~/AlphaResearch/research/<TICKER>/` (`inputs.json`, `narrative.py`, `reports/`).
- Last full evaluation: <date>. Consensus block dated <date>. Scheduled: <cron line or "manual">.
- Position: <none / long since … / size> (optional; the rules in `inputs.json` encode the discipline).

## Thesis (one paragraph) and the lines it moves

What the house believes that consensus does not, expressed as adjustments: which line, how many
percentage points, how long, in which scenario. Say what would prove it wrong.

## Scenario anchors

| | Bear | Base | Bull |
|---|---|---|---|
| Terminal growth | | | |
| Steady ROIC (own history: avg / low / now) | | | |
| Steady margin | | | |
| Multiple (own 5-year range low / avg / high) | | | |

## Company-specific data

- Segments and where the split is published (press-release table, 10-Q note).
- Multiple type and earnings basis (GAAP / adjusted) and why.
- Extra sources the thesis depends on (KPIs, transcripts, industry series) and the marketlens tools
  that reach them.
- Known quirks (fiscal year end, one-off tax items, lease treatment, share classes).

## What to watch at each print

Three to five concrete comparisons: model versus consensus for the adjusted lines, guidance items,
margin, capex.

## Log

- <date>: what changed and why (consensus refresh, assumption change, rule change, outcome of a print).
