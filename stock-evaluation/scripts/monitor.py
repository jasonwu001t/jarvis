"""Daily valuation monitor for one ticker folder: refresh the live inputs from atlas, rerun the engine, write reports.

What it refreshes automatically (official / exchange sources through atlas, http://127.0.0.1:8000):
  price            latest daily close (alpaca.stock_bars)             -> market.price
  risk-free rate   10-year Treasury, FRED DGS10                        -> wacc.risk_free   (if wacc.risk_free_mode == "dgs10")
  beta             2-year weekly raw beta vs SPY, Bloomberg-adjusted   -> wacc.beta        (if wacc.beta_mode == "adjusted_2y_weekly")
  fundamentals     SEC XBRL KPIs by fiscal quarter (sec.company_facts) -> new-quarter detection, actual vs consensus table
  earnings date    Nasdaq calendar via atlas

What stays manual (not available from official sources): sell-side consensus (the Bloomberg block),
segment revenue / operating income splits (press-release tables), the 5-year forward P/E range.

Usage (run from anywhere; --dir points at the ticker folder holding inputs.json, default: the current directory):
  python monitor.py --dir research/META                 # refresh, run, write reports/<date>.md + .html (and reports/latest.html)
  python monitor.py --dir research/META --apply-actuals # also write newly reported quarter(s) into inputs.json and roll latest_reported_q
  python monitor.py --dir research/META --offline       # no atlas calls: run the model on inputs.json as it is
A ticker folder may carry narrative.py (def sections(ctx) -> [(title, html)]) for the report's company-specific argument.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import statistics
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import valuation_engine as mm  # noqa: E402
import report_html  # noqa: E402


def _dir(argv):
    if "--dir" in argv:
        return os.path.abspath(argv[argv.index("--dir") + 1])
    return os.getcwd()


HERE = _dir(sys.argv)  # the ticker folder: inputs.json, optional narrative.py, reports/
ATLAS = os.environ.get("ATLAS_URL", "http://127.0.0.1:8000").rstrip("/")

# atlas XBRL KPI id -> inputs.json line (values in USD -> USD millions, per-share and shares handled below)
KPI_TO_LINE = {
    "revenue": "revenue", "operating_income": "operating_income", "pretax_income": "pretax_income",
    "income_tax_expense": "income_tax", "net_income": "net_income", "shares_diluted": "diluted_shares",
    "dividends_per_share": "dps", "dividends_paid": "dividends_total", "buybacks": "buybacks",
    "depreciation_amortization": "d_and_a", "share_comp": "sbc", "operating_cash_flow": "operating_cash_flow",
    "capex": "capex", "finance_lease_additions": "finance_lease_additions", "cash": "cash",
    "total_debt": "total_debt", "equity": "equity", "eps_diluted": "gaap_eps",
}
PER_SHARE = {"dividends_per_share", "eps_diluted"}
SHARES = {"shares_diluted"}


def get(path: str, **params) -> dict:
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(f"{ATLAS}{path}?{qs}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def period_key(period: str) -> int:
    """'2026-Q3' -> 20263, 'FY2026' -> 20260."""
    if period.startswith("FY"):
        return int(period[2:]) * 10
    y, q = period.split("-Q")
    return int(y) * 10 + int(q)


# ----------------------------------------------------------------------------------------- live data
def live_price(ticker: str) -> dict:
    rows = get(f"/api/v1/market/prices/{ticker}", limit=1)["data"]["rows"]
    return {"price": float(rows[0]["close"]), "date": rows[0]["as_of_date"]}


def live_dgs10() -> dict:
    rows = get("/api/v1/macro/series/DGS10", limit=1)["data"]["rows"]
    return {"value": float(rows[0]["value"]) / 100, "date": rows[0]["as_of_date"]}


def weekly_closes(ticker: str, limit: int = 560) -> dict[dt.date, float]:
    rows = get(f"/api/v1/market/prices/{ticker}", limit=limit)["data"]["rows"]
    by_week = {}
    for r in rows:                       # rows are newest first; keep the last trading day of each ISO week
        d = dt.date.fromisoformat(r["as_of_date"])
        wk = d.isocalendar()[:2]
        if wk not in by_week or d > by_week[wk][0]:
            by_week[wk] = (d, float(r["close"]))
    return {d: c for d, c in by_week.values()}


def live_beta(ticker: str, bench: str = "SPY", weeks: int = 104) -> dict:
    a, b = weekly_closes(ticker), weekly_closes(bench)
    dates = sorted(set(a) & set(b))
    # drop the current, unfinished week
    if dates and dates[-1] >= dt.date.today() - dt.timedelta(days=dt.date.today().weekday()):
        dates = dates[:-1]
    dates = dates[-(weeks + 1):]
    ra = [a[d1] / a[d0] - 1 for d0, d1 in zip(dates[:-1], dates[1:])]
    rb = [b[d1] / b[d0] - 1 for d0, d1 in zip(dates[:-1], dates[1:])]
    ma, mb = statistics.fmean(ra), statistics.fmean(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / (len(ra) - 1)
    raw = cov / statistics.variance(rb)
    return {"raw": raw, "adjusted": 0.67 * raw + 0.33, "n_weeks": len(ra), "from": str(dates[0]), "to": str(dates[-1])}


def live_kpis(ticker: str) -> dict[str, dict]:
    """{kpi id: {period key: value}} from atlas's XBRL KPI table, in USD millions (per-share and shares as is / millions)."""
    kpis = get(f"/api/v1/filings/ticker/{ticker}", top_n=1)["data"]["xbrl"]["kpis"]
    out = {}
    for k in kpis:
        series = {}
        for row in k.get("quarterly", []) + k.get("annual", []):
            v = row["value"]
            if v is None:
                continue
            if k["id"] in PER_SHARE:
                pass
            elif k["id"] in SHARES:
                v = v / 1e6
            else:
                v = v / 1e6
            series[period_key(row["period"])] = {"value": v, "end": row["end"], "filed": row.get("filed"), "form": row.get("form")}
        out[k["id"]] = series
    return out


def live_balance_sheet_extras(ticker: str, period_end: str) -> dict:
    """Marketable securities, equity-method and non-marketable equity investments, finance-lease liabilities at one date."""
    wanted = {"MarketableSecuritiesCurrent": "marketable_securities", "EquityMethodInvestments": "equity_method_investments",
              "EquitySecuritiesWithoutReadilyDeterminableFairValueAmount": "non_marketable_equity",
              "FinanceLeaseLiability": "finance_lease_liability", "LongTermDebt": "long_term_debt",
              "CashAndCashEquivalentsAtCarryingValue": "cash"}
    out = {}
    for metric, name in wanted.items():
        try:
            rows = get("/api/v1/data/datasets/sec.company_facts/rows", start=period_end, end=period_end, limit=5,
                       **{"eq.ticker": ticker, "eq.metric": metric})["data"]["rows"]
        except Exception as exc:  # noqa: BLE001
            out[name] = {"value": None, "error": str(exc)[:80]}
            continue
        vals = [r["value"] for r in rows if r.get("period_start") is None and r["value"] is not None]
        out[name] = {"value": vals[0] / 1e6 if vals else None}
    if out.get("finance_lease_liability", {}).get("value") is None:
        # only disclosed in the 10-K: carry the latest fiscal-year-end balance forward
        try:
            rows = get("/api/v1/data/datasets/sec.company_facts/rows", end=period_end, limit=50, order="desc",
                       **{"eq.ticker": ticker, "eq.metric": "FinanceLeaseLiability"})["data"]["rows"]
            vals = [(r["period_end"], r["value"]) for r in rows if r.get("period_start") is None and r["value"] is not None]
            if vals:
                vals.sort()
                out["finance_lease_liability"] = {"value": vals[-1][1] / 1e6, "carried_from": vals[-1][0]}
        except Exception as exc:  # noqa: BLE001
            out["finance_lease_liability"] = {"value": None, "error": str(exc)[:80]}
    return out


def live_earnings(ticker: str) -> dict:
    d = get(f"/api/v1/calendar/earnings/ticker/{ticker}")["data"]
    n = d.get("next") or {}
    return {"report_date": n.get("report_date"), "time_of_day": n.get("time_of_day"), "fiscal_quarter": n.get("fiscal_quarter"),
            "status": n.get("status"), "eps_consensus_nasdaq": (n.get("eps_forecast") or {}).get("value")}


# ------------------------------------------------------------------------------------- new quarters
def detect_new_quarters(inputs: dict, kpis: dict) -> list[int]:
    latest = inputs["as_of"]["latest_reported_fy"] * 10 + inputs["as_of"]["latest_reported_q"]
    reported = sorted(k for k in kpis.get("revenue", {}) if k % 10 != 0 and k > latest)
    return reported


def actual_vs_consensus(inputs: dict, kpis: dict, key: int) -> list[dict]:
    rows = []
    L = inputs["lines"]
    for kpi, line in KPI_TO_LINE.items():
        act = kpis.get(kpi, {}).get(key, {}).get("value")
        cons = L.get(line, {}).get(str(key)) if line in L else None
        if kpi == "eps_diluted":
            ni, sh = L.get("net_income", {}).get(str(key)), L.get("diluted_shares", {}).get(str(key))
            cons = ni / sh if ni and sh else None
        if act is None and cons is None:
            continue
        rows.append({"kpi": kpi, "line": line, "actual": act, "consensus": cons,
                     "surprise": (act / cons - 1) if (act is not None and cons) else None})
    return rows


def apply_actuals(inputs: dict, kpis: dict, keys: list[int], extras_by_key: dict) -> list[str]:
    """Write the reported quarter(s) into inputs.json lines and roll the as-of markers. Returns notes."""
    notes = []
    L = inputs["lines"]
    for key in keys:
        for kpi, line in KPI_TO_LINE.items():
            v = kpis.get(kpi, {}).get(key, {}).get("value")
            if v is None or line in ("cash", "total_debt", "gaap_eps"):
                continue
            L.setdefault(line, {})[str(key)] = round(v, 6)
        ex = extras_by_key.get(key, {})
        cash = kpis.get("cash", {}).get(key, {}).get("value")
        ms = (ex.get("marketable_securities") or {}).get("value")
        if cash is not None and ms is not None:
            L.setdefault("cash_and_st_investments", {})[str(key)] = round(cash + ms, 6)
        else:
            notes.append(f"{key}: cash_and_st_investments left blank (cash={cash}, marketable securities={ms})")
        ltd = (ex.get("long_term_debt") or {}).get("value") or kpis.get("total_debt", {}).get(key, {}).get("value")
        fl = (ex.get("finance_lease_liability") or {}).get("value")
        if ltd is not None:
            L.setdefault("debt", {})[str(key)] = round(ltd + (fl or 0.0), 6)
            if fl is None:
                notes.append(f"{key}: debt excludes finance-lease liabilities (only disclosed in the 10-K)")
            elif (ex.get("finance_lease_liability") or {}).get("carried_from"):
                notes.append(f"{key}: finance-lease liability carried forward from {ex['finance_lease_liability']['carried_from']} (10-K only)")
        em, nm = (ex.get("equity_method_investments") or {}).get("value"), (ex.get("non_marketable_equity") or {}).get("value")
        if em is not None and nm is not None:
            L.setdefault("investments", {})[str(key)] = round(em + nm, 6)
        L.setdefault("minority_interest", {})[str(key)] = 0.0
        # the template's "other income" = pretax - operating income
        if L.get("pretax_income", {}).get(str(key)) is not None and L.get("operating_income", {}).get(str(key)) is not None:
            L.setdefault("other_income", {})[str(key)] = round(L["pretax_income"][str(key)] - L["operating_income"][str(key)], 6)
        for p in inputs["periods"]:
            if int(p["key"]) == key:
                p["status"] = "actual"
        notes.append(f"{key}: segment lines (Family of Apps / Advertising / Other Revenue / Reality Labs) must be keyed in from the press release")
        end = kpis["revenue"][key]["end"]
        inputs["as_of"]["latest_reported_fy"], inputs["as_of"]["latest_reported_q"] = key // 10, key % 10
        inputs["as_of"]["balance_sheet_date"] = end
    return notes


# ------------------------------------------------------------------------------------------- report
def pct(x, d=1):
    return "—" if x is None else f"{x * 100:+.{d}f}%"


def money(x, d=0):
    return "—" if x is None else f"{x:,.{d}f}"


def rules(inputs: dict, out: dict) -> list[dict]:
    """Position rules from inputs.monitor.rules, evaluated on the model output."""
    price = out["price"]
    h, s = out["house"], out["scenarios"]
    ctx = {"price": price, "house_target": h["target"], "house_upside": h["upside"], "bear_target": s["bear"]["blended_target"],
           "base_target": s["base"]["blended_target"], "bull_target": s["bull"]["blended_target"],
           "price_implied_pe_base": s["base"]["multiples"]["price_implied_multiple"],
           "pe5y_low": (inputs.get("reference_multiples") or {}).get("pe5y_low"),
           "pe5y_high": (inputs.get("reference_multiples") or {}).get("pe5y_high")}
    res = []
    for r in inputs.get("monitor", {}).get("rules", []):
        try:
            fired = bool(eval(r["when"], {"__builtins__": {}}, ctx))  # noqa: S307 - expressions come from the user's own inputs.json
        except Exception as exc:  # noqa: BLE001
            fired, r = False, {**r, "action": f"rule error: {exc}"}
        res.append({"name": r["name"], "fired": fired, "action": r["action"], "when": r["when"], "exposure": r.get("exposure")})
    return res


def render(inputs: dict, out: dict, live: dict, new_q: list[int], avc: dict, applied_notes: list[str]) -> str:
    a = inputs["as_of"]
    s, h, w = out["scenarios"], out["house"], out["wacc"]
    base = inputs.get("baseline", {})
    today = dt.date.today().isoformat()
    L = []
    L.append(f"# {inputs['company']['ticker']} valuation monitor — {today}")
    L.append("")
    L.append(f"Price ${out['price']:,.2f} ({live.get('price', {}).get('date', inputs['market'].get('price_date'))}) · "
             f"latest reported quarter FY{a['latest_reported_fy']} Q{a['latest_reported_q']} (balance sheet {a['balance_sheet_date']}) · "
             f"consensus block dated {a['consensus_date']}")
    e = live.get("earnings") or {}
    if e.get("report_date"):
        L.append(f"Next earnings: **{e['report_date']}** ({e.get('time_of_day')}, {e.get('fiscal_quarter')}), Nasdaq EPS consensus {e.get('eps_consensus_nasdaq')}")
    L.append("")
    L.append("## Targets (12 months forward, per share)")
    L.append("")
    L.append(f"| Scenario | DCF | P/E | Blended | vs price | {base.get('label', 'Baseline')} |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for k in ("bear", "base", "bull"):
        L.append(f"| {k} | {money(s[k]['dcf']['target'])} | {money(s[k]['multiples']['target'])} | **{money(s[k]['blended_target'])}** | "
                 f"{pct(s[k]['upside'])} | {money(base.get(k))} |")
    L.append(f"| **house (position {h['position']:+.0%} toward bull)** | {money(h['dcf_target'])} | {money(h['multiples_target'])} | "
             f"**{money(h['target'])}** | **{pct(h['upside'])}** | {money(base.get('house'))} |")
    L.append("")
    L.append("## Rules")
    L.append("")
    for r in rules(inputs, out):
        L.append(f"- {'🔴' if r['fired'] else '⚪'} **{r['name']}**" + (f" (position {r['exposure']:.0%})" if r.get('exposure') is not None else "") + f" — {r['action']}  `{r['when']}`")
    L.append("")
    L.append("## Live inputs")
    L.append("")
    b = live.get("beta") or {}
    L.append(f"- Risk-free (10y UST, {live.get('dgs10', {}).get('date', 'manual')}): {inputs['wacc']['risk_free']:.2%}"
             + (f" (baseline {base['risk_free']:.2%})" if base.get('risk_free') is not None else ""))
    L.append(f"- Beta: {inputs['wacc']['beta']:.3f}" + (f" (raw 2y weekly vs SPY {b['raw']:.3f}, n={b['n_weeks']}, {b['from']}..{b['to']}" + (f"; baseline {base['beta']:.3f}" if base.get('beta') is not None else "") + ")" if b else " (manual)"))
    L.append(f"- Cost of equity {w['cost_of_equity']:.2%}, after-tax cost of debt {w['after_tax_cost_of_debt']:.2%} (TTM tax {w['ttm_tax_rate']:.1%}), "
             f"E/V {w['weight_equity']:.1%} → WACC **{w['wacc']:.2%}**" + (f" (baseline {base['wacc']:.2%})" if base.get('wacc') is not None else ""))
    bm = s["base"]["multiples"]
    L.append(f"- Price-implied P/E on quarters 5-8 GAAP EPS (${bm['q5_q8_eps']:.2f}): {bm['price_implied_multiple']:.1f}x "
             f"vs target {inputs['scenarios']['base']['target_multiple']:.0f}x; own 5-year forward range {inputs['reference_multiples']['pe5y_low']}x / {inputs['reference_multiples']['pe5y_avg']}x / {inputs['reference_multiples']['pe5y_high']}x")
    L.append(f"- Base case: revenue CAGR FY{a['latest_reported_fy']-1}-FY{a['latest_reported_fy']+4} {s['base']['revenue_cagr_5y']:.1%}, "
             f"quarters 5-8 operating margin {s['base']['q5_q8_operating_margin']:.1%}, terminal value {s['base']['dcf']['terminal_share_of_ev']:.0%} of EV")
    L.append("")
    L.append("## Checks")
    L.append("")
    for c in out["checks"]:
        flag = "✓" if c["ok"] else ("！" if c.get("warn_only") else "✗")
        val = c["value"]
        if isinstance(val, float):
            val = f"{val:.4f}"
        elif isinstance(val, list):
            val = ", ".join(f"{x:.3f}" if isinstance(x, float) else str(x) for x in val)
        L.append(f"- {flag} {c['check']}: {val}")
    L.append("")
    L.append("## Reported quarters since the consensus block")
    L.append("")
    if not new_q:
        L.append(f"None yet: SEC XBRL shows FY{a['latest_reported_fy']} Q{a['latest_reported_q']} as the latest 10-Q/10-K.")
    for key in new_q:
        L.append(f"**FY{key // 10} Q{key % 10} is filed.** Actual vs the consensus the model was carrying (USD m; EPS and DPS per share; shares m):")
        L.append("")
        L.append("| KPI | Actual | Consensus | Surprise |")
        L.append("|---|---:|---:|---:|")
        for r in avc.get(key, []):
            L.append(f"| {r['kpi']} | {money(r['actual'], 2 if r['kpi'] in PER_SHARE else 0)} | {money(r['consensus'], 2 if r['kpi'] in PER_SHARE else 0)} | {pct(r['surprise'])} |")
        L.append("")
        L.append("To roll the model: run the monitor with `--apply-actuals`, then key in the segment lines from the press release and refresh the consensus block.")
    if applied_notes:
        L.append("")
        L.append("Applied to inputs.json:")
        for n in applied_notes:
            L.append(f"- {n}")
    L.append("")
    L.append("## Not refreshed automatically")
    L.append("")
    L.append("- Sell-side consensus for the unreported quarters and FY+1/FY+2: manual block in inputs.json.")
    L.append("- Segment revenue and operating income: press-release tables, manual.")
    L.append("- 5-year forward P/E range (low/avg/high): manual.")
    L.append("")
    L.append("_Generated by the stock-evaluation skill (scripts/monitor.py) from this folder's inputs.json; valuation logic in scripts/valuation_engine.py._")
    return "\n".join(L)


# --------------------------------------------------------------------------------------------- main
def main(argv: list[str]) -> int:
    offline = "--offline" in argv
    apply = "--apply-actuals" in argv
    path = os.path.join(HERE, "inputs.json")
    inputs = mm.load(path)
    live, new_q, avc, notes = {}, [], {}, []
    if not offline:
        t = inputs["company"]["ticker"]
        try:
            live["price"] = live_price(t)
            inputs["market"]["price"], inputs["market"]["price_date"] = live["price"]["price"], live["price"]["date"]
            inputs["market"]["market_cap_musd_override"] = None  # live mode: market cap = price x diluted shares
        except Exception as exc:  # noqa: BLE001
            live["price"] = {"error": str(exc)}
        if inputs["wacc"].get("risk_free_mode", "dgs10") == "dgs10":
            try:
                live["dgs10"] = live_dgs10()
                inputs["wacc"]["risk_free"] = live["dgs10"]["value"]
            except Exception as exc:  # noqa: BLE001
                live["dgs10"] = {"error": str(exc)}
        if inputs["wacc"].get("beta_mode", "adjusted_2y_weekly") == "adjusted_2y_weekly":
            try:
                live["beta"] = live_beta(t)
                inputs["wacc"]["beta"] = live["beta"]["adjusted"]
            except Exception as exc:  # noqa: BLE001
                live["beta"] = {"error": str(exc)}
        try:
            live["earnings"] = live_earnings(t)
        except Exception as exc:  # noqa: BLE001
            live["earnings"] = {"error": str(exc)}
        try:
            kpis = live_kpis(t)
            new_q = detect_new_quarters(inputs, kpis)
            extras = {}
            for key in new_q:
                avc[key] = actual_vs_consensus(inputs, kpis, key)
                extras[key] = live_balance_sheet_extras(t, kpis["revenue"][key]["end"])
            if apply and new_q:
                notes = apply_actuals(inputs, kpis, new_q, extras)
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(inputs, fh, indent=1, ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001
            live["kpis"] = {"error": str(exc)}
    out = mm.Model(inputs).run()
    report = render(inputs, out, live, new_q, avc, notes)
    os.makedirs(os.path.join(HERE, "reports"), exist_ok=True)
    rp = os.path.join(HERE, "reports", f"{dt.date.today().isoformat()}.md")
    with open(rp, "w", encoding="utf-8") as fh:
        fh.write(report + "\n")
    page = report_html.render(inputs, out, live, new_q, avc, notes, rules(inputs, out), HERE)
    hp = os.path.join(HERE, "reports", f"{dt.date.today().isoformat()}.html")
    for p in (hp, os.path.join(HERE, "reports", "latest.html")):
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(page)
    print(report)
    print(f"\n[written {os.path.relpath(rp, os.getcwd())}, {os.path.relpath(hp, os.getcwd())}, {os.path.relpath(os.path.join(HERE, 'reports', 'latest.html'), os.getcwd())}]", file=sys.stderr)
    errs = {k: v for k, v in live.items() if isinstance(v, dict) and "error" in v}
    if errs:
        print(f"[live fetch errors: {errs}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
