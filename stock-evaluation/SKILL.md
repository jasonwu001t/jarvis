---
name: stock-evaluation
description: Evaluate a stock or ETF the way an institutional analyst would and keep the evaluation alive — three-scenario DCF plus a forward-multiple leg, an explicit investment thesis, a comprehensive HTML report a reader can make the call from, and a daily monitor that re-underwrites the position on live prices, yields, beta and newly filed quarters. Use this skill whenever the user asks to evaluate, value, analyse, model, underwrite, re-rate or monitor a ticker or fund (e.g. "help me evaluate NVDA", "is AAPL worth it at this price", "build a valuation model for AMZN", "what's QQQ worth", "should I add to my META position", "re-run the META valuation", "what does the latest quarter do to the thesis"), even if they don't say "DCF" or "model". Ticker-specific playbooks live in tickers/<TICKER>.md; start there when one exists, scaffold one when it doesn't.
when_to_use: Any request to evaluate, value, model, monitor or re-underwrite a specific stock, ETF or position; any "is X cheap/expensive", "target price for X", "should I hold/add/trim X", "update the X model after earnings". Not for broad market commentary, macro-only questions, portfolio accounting, or trade execution.
---

# Stock evaluation

Produces, for one ticker: a working valuation model (`inputs.json`), a comprehensive HTML report
(the call, the argument, the full model, sensitivities, monitor) and a daily monitor that keeps the
numbers current and tells the user whether the position still makes sense. The first instance is
META (`tickers/META.md`, live in `~/AlphaResearch/research/META/`); every new ticker reuses the
same engine and report and adds its own playbook.

## Workflow

1. **Resolve the ticker and look for a playbook.** `ls tickers/` — if `<TICKER>.md` exists, read it
   first: it carries the thesis, the data sources that matter for that company, the watch items and
   the location of the live folder. If it does not exist, this is a new evaluation: read
   `tickers/_TEMPLATE.md` and plan to write `tickers/<TICKER>.md` at the end.
2. **Read the method once.** `references/valuation-method.md` is the engine's logic in English
   (three scenarios, convergence, terminal value, the P/E leg, the blend, the checks). You need it to
   fill inputs sensibly and to explain the output; you do not need to re-derive it.
3. **Gather data** following `references/data-sources.md`. Everything official (SEC XBRL history,
   price, 10-year yield, beta, earnings date) comes from marketlens / atlas and the monitor refreshes
   it; the three manual blocks (sell-side consensus, segment splits, the forward-multiple range) are
   keyed in and date-stamped. Say plainly which inputs are manual and how old they are.
4. **Build or update the ticker folder** `~/AlphaResearch/research/<TICKER>/`:
   - new ticker: `python3 scripts/new_ticker.py <TICKER> "<Company name>" --dir ~/AlphaResearch/research/<TICKER>`
     scaffolds `inputs.json` with the schema and comments, then fill the history, consensus,
     scenario assumptions and adjustments (see `references/inputs-schema.md`);
   - existing ticker: edit `inputs.json` (consensus block, assumptions, adjustments, rules);
   - write `narrative.py` for the company-specific argument (the META one is the pattern); without it
     the report renders a generic method walkthrough.
5. **Run** `python3 scripts/monitor.py --dir ~/AlphaResearch/research/<TICKER>` (`--offline` without
   atlas). Read the summary the engine prints and the check list; a failed check means an input is
   wrong, not that the stock is. `reports/latest.html` is the deliverable: open it and look at it
   before handing it over.
6. **Report back** with the call, not the mechanics: price versus bear / base / bull, the house target
   and upside, the rule in force, what the next print has to show, and which manual inputs the number
   depends on. Point at the HTML.
7. **Keep it alive.** `references/monitoring.md` covers the daily protocol, the rules, rolling a newly
   filed quarter with `--apply-actuals`, and scheduling (the META job in AlphaResearch's crontab is the
   pattern). After an earnings print, re-underwrite: actuals versus the consensus the model carried,
   then the segment split and a fresh consensus block.
8. **Write the playbook.** Finish a new ticker by writing `tickers/<TICKER>.md` from the template so
   the next evaluation starts from what was learned.

## What makes evaluations differ, and what stays the same

Same for every name: the engine, the report layout, the official data pipeline, the checks, the
rules mechanism. Different per name, and captured in the playbook: the thesis and the lines it
adjusts (ads and capex for META; cloud growth and margins for a hyperscaler; deliveries and ASP for
an automaker), the segment definitions, which multiple fits (P/E for mature earners, EV/EBITDA for
heavy D&A, P/S for pre-profit), the earnings basis (GAAP versus adjusted), the steady-state anchors
(use the company's own ROIC and margin history), and the extra sources worth reading (press-release
tables, transcripts, industry data).

An ETF or index fund does not get a DCF: value it bottom-up from its holdings' evaluations or
top-down on the index's forward multiple and earnings growth; say which, and keep the monitor to
price, yield, flows and the multiple. Note the choice in the playbook.

## Honesty rules that matter here

- The engine replicates a published template to the dollar on its own inputs; the output is only as
  good as the consensus block and the three steady-state assumptions. Show the sensitivities.
- Never present a manual input as refreshed. The report labels the manual blocks and their dates.
- The rules in `inputs.json` are the user's position discipline, not advice; evaluate them, report
  which fired, and leave the decision to the user.
- Reported financials come from SEC XBRL only; no data vendors (AlphaResearch policy).

## Files

| Path | Purpose |
|---|---|
| `scripts/valuation_engine.py` | The model: three-scenario DCF + P/E, blend, house target, checks, full period table. |
| `scripts/report_html.py` | The HTML report renderer (loads the ticker folder's `narrative.py` when present). |
| `scripts/monitor.py` | Refresh live inputs from atlas, run the engine, write `reports/<date>.md/.html`; `--apply-actuals` rolls a filed quarter. |
| `scripts/new_ticker.py` | Scaffold a ticker folder with a commented `inputs.json`. |
| `references/valuation-method.md` | The method in English. |
| `references/data-sources.md` | marketlens / atlas tool map: what is live, what is manual, how to fetch each. |
| `references/inputs-schema.md` | Every key in `inputs.json`. |
| `references/report-spec.md` | What the HTML report contains and the UX rules it follows. |
| `references/monitoring.md` | Daily protocol, rules, rolling quarters, scheduling. |
| `tickers/_TEMPLATE.md`, `tickers/<TICKER>.md` | Per-ticker playbooks. |
