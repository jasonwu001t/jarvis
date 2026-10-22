"""Point-in-time backtest of the valuation model and its position rules for one ticker folder.

For every quarterly filing in the window, rebuild inputs.json as it could have been built on the filing day
(SEC XBRL actuals known by then, the 10-year yield and a 2-year weekly beta on that day, the close on that
day), run the engine, read which rule fired, and simulate the position the rules imply. Two consensus
variants, because historical sell-side consensus is not available from official sources:

  momentum   - a mechanical "street" built only from data known on the day: trailing-twelve-month revenue
               growth fading 20% a year, flat TTM operating margin and tax rate, capex on its own TTM growth,
               D&A / SBC at TTM ratios, flat shares and DPS.  No look-ahead.
  foresight  - the same, but where the forecast periods have since been reported, the reported figures are
               used (a perfect-foresight street).  An upper bound on what good forecasts would have done.

Everything else (scenario assumptions, adjustments, rules, ERP, cost of debt, the 5-year multiple range) is
taken from the folder's inputs.json as it is today; adjustments keyed to absolute periods are re-keyed to
the same relative periods (remaining quarters, FY+1, FY+2). Segments are dropped (not in XBRL), so a segment
adjustment becomes a total-revenue adjustment with the same percentage points.

  python3 backtest.py --dir research/META [--since 2023-10-01] [--lag 2] [--out research/META/backtest]

Evaluation dates are each earnings release (8-K item 2.02) plus --lag trading days (default 2): the user looks at the
model two days after the call and rebalances at that close. The just-reported quarter counts as known on the release.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import statistics
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import valuation_engine as mm  # noqa: E402
import overlays  # noqa: E402
import guidance as guid  # noqa: E402
from monitor import KPI_TO_LINE, PER_SHARE, SHARES, period_key  # noqa: E402

ATLAS = os.environ.get("ATLAS_URL", "http://127.0.0.1:8000").rstrip("/")
EXTRA_CONCEPTS = {"MarketableSecuritiesCurrent": "marketable_securities", "EquityMethodInvestments": "equity_method",
                  "EquitySecuritiesWithoutReadilyDeterminableFairValueAmount": "non_marketable",
                  "FinanceLeaseLiability": "finance_lease_liability"}


def get(path: str, **params) -> dict:
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    with urllib.request.urlopen(urllib.request.Request(f"{ATLAS}{path}?{qs}", headers={"Accept": "application/json"}), timeout=120) as r:
        return json.load(r)


VARIANTS = {
    # name: street, sizing (rules | ev), overlays, model improvements (rate-aware multiple + ROIC anchor)
    "momentum_rules": ("momentum", "rules", False, False),
    "guidance_rules": ("guidance", "rules", False, False),
    "guidance_ev": ("guidance", "ev", False, True),
    "guidance_ev_overlays": ("guidance", "ev", True, True),
    "foresight_rules": ("foresight", "rules", False, False),
}


# ------------------------------------------------------------------------------------------ data
def fetch_all(ticker: str, folder: str, since: str) -> dict:
    kpis = get(f"/api/v1/filings/ticker/{ticker}", top_n=1)["data"]["xbrl"]["kpis"]
    K = {}
    for k in kpis:
        rows = []
        for r in k.get("quarterly", []) + k.get("annual", []):
            if r["value"] is None:
                continue
            v = r["value"] if k["id"] in PER_SHARE else r["value"] / 1e6
            rows.append({"key": period_key(r["period"]), "end": r["end"], "filed": r.get("filed"), "value": v, "kind": r["kind"]})
        K[k["id"]] = rows
    px = {t: {r["as_of_date"]: float(r["close"]) for r in get(f"/api/v1/market/prices/{t}", limit=1500)["data"]["rows"]} for t in (ticker, "SPY")}
    rf = {r["as_of_date"]: float(r["value"]) / 100 for r in get("/api/v1/macro/series/DGS10", limit=2000)["data"]["rows"]}
    macro = {}
    for sid, name, scale in (("NFCI", "nfci", 1.0), ("VIXCLS", "vix", 1.0), ("BAA10Y", "baa10y", 0.01)):
        macro[name] = {r["as_of_date"]: float(r["value"]) * scale for r in get(f"/api/v1/macro/series/{sid}", limit=2000)["data"]["rows"] if r["value"] is not None}
    gsince = (dt.date.fromisoformat(since) - dt.timedelta(days=400)).isoformat()
    guidance_rows = [r for r in guid.collect(ticker, folder, since=gsince) if r.get("parsed")]
    extras = {}
    for concept, name in EXTRA_CONCEPTS.items():
        rows = get("/api/v1/data/datasets/sec.company_facts/rows", start="2020-01-01", limit=500, **{"eq.ticker": ticker, "eq.metric": concept})["data"]["rows"]
        extras[name] = [{"end": r["period_end"], "known": r["knowledge_time"][:10], "value": r["value"] / 1e6}
                        for r in rows if r.get("period_start") is None and r["value"] is not None]
    return {"kpis": K, "prices": px, "rf": rf, "extras": extras, "macro": macro, "guidance": guidance_rows}


def last_on_or_before(series: dict, d: str):
    keys = [k for k in series if k <= d]
    return series[max(keys)] if keys else None


def beta_at(px: dict, bench: dict, d: str, weeks: int = 104):
    def weekly(s):
        by = {}
        for ds, c in s.items():
            if ds > d:
                continue
            dd = dt.date.fromisoformat(ds)
            wk = dd.isocalendar()[:2]
            if wk not in by or dd > by[wk][0]:
                by[wk] = (dd, c)
        return {a: b for a, b in by.values()}
    a, b = weekly(px), weekly(bench)
    dates = sorted(set(a) & set(b))[-(weeks + 1):]
    if len(dates) < 30:
        return None
    ra = [a[d1] / a[d0] - 1 for d0, d1 in zip(dates[:-1], dates[1:])]
    rb = [b[d1] / b[d0] - 1 for d0, d1 in zip(dates[:-1], dates[1:])]
    ma, mb = statistics.fmean(ra), statistics.fmean(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / (len(ra) - 1)
    raw = cov / statistics.variance(rb)
    return {"raw": raw, "adjusted": 0.67 * raw + 0.33, "n": len(ra)}


# ------------------------------------------------------------------------------- inputs on a day
def build_inputs(template: dict, data: dict, eval_key: int, eval_date: str, variant: str, improvements: bool = False) -> dict:
    K = data["kpis"]
    fy, q = eval_key // 10, eval_key % 10
    def is_known(k):   # reported by the earnings release of eval_key: every earlier period, and the fiscal year once Q4 is out
        return (k % 10 != 0 and k <= eval_key) or (k % 10 == 0 and (k // 10 < fy or q == 4))
    known = lambda rows: {r["key"]: r["value"] for r in rows if is_known(r["key"])}
    everything = lambda rows: {r["key"]: r["value"] for r in rows}
    inp = copy.deepcopy(template)
    inp["segments"] = {}
    inp["lines"] = {}
    inp["baseline"] = {}
    L = inp["lines"]
    for kpi, line in KPI_TO_LINE.items():
        if kpi in ("cash", "total_debt", "eps_diluted"):
            continue
        L[line] = known(K.get(kpi, []))
    # balance sheet composites at every known quarter end
    ext = data["extras"]
    def ext_at(name, end, d):
        vals = [r for r in ext[name] if r["end"] <= end and r["known"] <= (dt.date.fromisoformat(d) + dt.timedelta(days=14)).isoformat()]
        vals.sort(key=lambda r: r["end"])
        return vals[-1]["value"] if vals else 0.0
    ends = {r["key"]: r["end"] for r in K["revenue"] if is_known(r["key"])}
    cash = known(K.get("cash", []))
    debt = known(K.get("total_debt", []))
    L["cash_and_st_investments"] = {k: cash[k] + ext_at("marketable_securities", ends[k], eval_date) for k in cash if k in ends}
    L["debt"] = {k: debt[k] + ext_at("finance_lease_liability", ends[k], eval_date) for k in debt if k in ends}
    L["investments"] = {k: ext_at("equity_method", ends[k], eval_date) + ext_at("non_marketable", ends[k], eval_date) for k in ends}
    L["minority_interest"] = {k: 0.0 for k in ends}
    L["other_income"] = {k: L["pretax_income"][k] - L["operating_income"][k] for k in L["pretax_income"] if k in L["operating_income"]}
    L["adjustments"] = {k: 0.0 for k in L["net_income"]}
    L["adjusted_net_income"] = dict(L["net_income"])
    L["wc_increase"] = {k: 0.0 for k in L["revenue"]}
    for name in ("dps", "dividends_total", "buybacks", "finance_lease_additions", "sbc", "d_and_a"):
        L.setdefault(name, {})
    # ---- the "street": remaining quarters of the current FY, FY, FY+1, FY+2
    rq = [fy * 10 + k for k in range(q + 1, 5)]
    fy0, y1, y2 = fy * 10, (fy + 1) * 10, (fy + 2) * 10
    rev = L["revenue"]
    qkeys = sorted(k for k in rev if k % 10 != 0)
    last4 = qkeys[-4:]
    prev4 = qkeys[-8:-4]
    ttm = lambda line, ks: sum(L[line].get(k, 0.0) for k in ks)
    g = ttm("revenue", last4) / ttm("revenue", prev4) - 1 if ttm("revenue", prev4) else 0.1
    g_capex = ttm("capex", last4) / ttm("capex", prev4) - 1 if ttm("capex", prev4) else g
    # guidance street: the release that reported eval_key guides the next quarter's revenue and the fiscal year's capex
    gd = None
    if variant in ("guidance",):
        cands = [r for r in data.get("guidance", []) if r["date"] <= eval_date and r.get("revenue_next_quarter")
                 and r["revenue_next_quarter"]["period_key"] > eval_key]
        gd = cands[-1] if cands else None
    g_next_q, capex_fy_mid, beat = None, None, 1.0
    if gd:
        # how the company has landed against its own midpoint in the quarters already reported by eval_date (last 6 guided quarters)
        hist = []
        for r in data.get("guidance", []):
            if r["date"] < gd["date"] and r.get("revenue_next_quarter"):
                k = r["revenue_next_quarter"]["period_key"]
                if is_known(k) and rev.get(k):
                    hist.append(rev[k] / r["revenue_next_quarter"]["mid"])
        beat = statistics.fmean(hist[-6:]) if hist else 1.0
        rv = gd["revenue_next_quarter"]
        prior = rev.get(rv["period_key"] - 10)
        if prior:
            g_next_q = rv["mid"] * beat / prior - 1
            g = g_next_q                       # the company's own near-term growth (beat-adjusted) replaces the trailing rate
        cx = gd.get("capex_full_year")
        if cx and cx["period_key"] == fy * 10:
            capex_fy_mid = cx["mid"]
            last_fy_capex = L["capex"].get((fy - 1) * 10)
            if last_fy_capex:
                g_capex = capex_fy_mid / last_fy_capex - 1
    margin = ttm("operating_income", last4) / ttm("revenue", last4)
    tax = min(0.30, max(0.10, ttm("income_tax", last4) / ttm("pretax_income", last4))) if ttm("pretax_income", last4) > 0 else 0.15
    da_r = ttm("d_and_a", last4) / ttm("revenue", last4)
    sbc_r = ttm("sbc", last4) / ttm("revenue", last4)
    def latest(line, default=0.0):   # newest known value of a line (Q4 per-share and share counts are not derived)
        ks = [k for k in L.get(line, {}) if k <= eval_key and k % 10 != 0] or [k for k in L.get(line, {}) if k <= eval_key]
        return L[line][max(ks)] if ks else default
    shares = latest("diluted_shares")
    dps_q = latest("dps")
    L["diluted_shares"].setdefault(eval_key, shares)   # the engine reads both at the latest reported quarter
    L["dps"].setdefault(eval_key, dps_q)
    lease_r = 0.0
    fy_leases = {k: v for k, v in L["finance_lease_additions"].items() if k % 10 == 0}
    if fy_leases:
        kk = max(fy_leases)
        lease_r = fy_leases[kk] / L["capex"][kk] if L["capex"].get(kk) else 0.0
    actual_all = {line: everything(K.get(kpi, [])) for kpi, line in KPI_TO_LINE.items()}

    def put(k, revenue, capex):
        oi = revenue * margin
        ni = (oi + 0.0) * (1 - tax)
        vals = {"revenue": revenue, "operating_income": oi, "pretax_income": oi, "income_tax": oi * tax, "net_income": ni,
                "adjustments": 0.0, "adjusted_net_income": ni, "diluted_shares": shares, "dps": dps_q * (4 if k % 10 == 0 else 1),
                "dividends_total": dps_q * shares * (4 if k % 10 == 0 else 1), "d_and_a": revenue * da_r, "sbc": revenue * sbc_r,
                "wc_increase": 0.0, "capex": capex, "finance_lease_additions": capex * lease_r, "other_income": 0.0}
        if variant == "foresight":
            for line in ("revenue", "operating_income", "pretax_income", "income_tax", "net_income", "diluted_shares", "dps",
                         "dividends_total", "d_and_a", "sbc", "capex", "finance_lease_additions"):
                if actual_all.get(line, {}).get(k) is not None:
                    vals[line] = actual_all[line][k]
            if actual_all.get("pretax_income", {}).get(k) is not None and actual_all.get("operating_income", {}).get(k) is not None:
                vals["other_income"] = actual_all["pretax_income"][k] - actual_all["operating_income"][k]
            vals["adjusted_net_income"] = vals["net_income"]
        for line, v in vals.items():
            L.setdefault(line, {})[k] = v

    ytd_capex = sum(L["capex"].get(fy * 10 + i, 0.0) for i in range(1, q + 1))
    prior_rq = [L["capex"].get(k - 10, 0.0) for k in rq]
    for k in rq:
        capex_k = L["capex"].get(k - 10, L["capex"].get(last4[-1], 0.0)) * (1 + g_capex)
        if capex_fy_mid and sum(prior_rq) > 0:
            capex_k = max(0.0, capex_fy_mid - ytd_capex) * (L["capex"].get(k - 10, 0.0) / sum(prior_rq))
        rev_k = rev.get(k - 10, rev[last4[-1]]) * (1 + g)
        if gd and k == gd["revenue_next_quarter"]["period_key"]:
            rev_k = gd["revenue_next_quarter"]["mid"] * beat
        put(k, rev_k, capex_k)
    fy_rev = sum(L["revenue"][fy * 10 + i] for i in range(1, 5))
    fy_capex = sum(L["capex"][fy * 10 + i] for i in range(1, 5))
    put(fy0, fy_rev, fy_capex)
    put(y1, L["revenue"][fy0] * (1 + g * 0.8), L["capex"][fy0] * (1 + g_capex * 0.8))
    put(y2, L["revenue"][y1] * (1 + g * 0.64), L["capex"][y1] * (1 + g_capex * 0.64))
    # periods: actual quarters and years of the last four fiscal years, then the street
    periods = []
    for k in sorted(rev):
        if k <= eval_key and k // 10 >= fy - 4 and (k % 10 != 0 or k // 10 < fy):
            periods.append({"key": k, "year": k // 10, "q": k % 10, "status": "actual"})
    for k in rq + [fy0, y1, y2]:
        periods.append({"key": k, "year": k // 10, "q": k % 10, "status": "consensus"})
    inp["periods"] = periods
    for line in list(L):
        L[line] = {str(k): v for k, v in L[line].items()}
    # adjustments re-keyed to relative periods; segment lines become total revenue
    tmpl_fy = template["as_of"]["latest_reported_fy"] * 10
    adj = []
    for r in template["adjustments"]:
        pk = int(r["period_key"])
        line = "Total revenue" if r["line"] not in mm.CAPEX_LINE_ALIASES | mm.REVENUE_LINE_ALIASES | mm.MARGIN_LINE_ALIASES else r["line"]
        if pk % 10 != 0:
            targets = rq
        elif pk == tmpl_fy + 10:
            targets = [y1]
        elif pk == tmpl_fy + 20:
            targets = [y2]
        else:
            targets = []
        for t in targets:
            if not any(a["line"] == line and a["period_key"] == t for a in adj):
                adj.append({"line": line, "period_key": t, "bear": r["bear"], "base": r["base"], "bull": r["bull"]})
    inp["adjustments"] = adj
    end = ends[eval_key]
    inp["as_of"].update({"latest_reported_fy": fy, "latest_reported_q": q, "balance_sheet_date": end, "consensus_date": eval_date,
                         "consensus_source": f"backtest {variant} street"})
    price = last_on_or_before(data["prices"][template["company"]["ticker"]], eval_date)
    inp["market"].update({"price": price, "price_date": eval_date, "market_cap_musd_override": None})
    b = beta_at(data["prices"][template["company"]["ticker"]], data["prices"]["SPY"], eval_date)
    inp["wacc"]["beta"] = b["adjusted"] if b else template["wacc"]["beta"]
    inp["wacc"]["risk_free"] = last_on_or_before(data["rf"], eval_date) or template["wacc"]["risk_free"]
    inp["_street"] = {"g_ttm": g, "g_capex_ttm": g_capex, "margin_ttm": margin, "tax_ttm": tax, "beta_raw": b["raw"] if b else None,
                      "guidance_used": bool(gd), "guidance_date": gd["date"] if gd else None, "guidance_beat": beat if gd else None}
    if not improvements:
        inp["blend"]["multiple_rate_aware"] = {"enabled": False}
        inp["blend"]["steady_roic_anchor"] = {"enabled": False}
    return inp


# --------------------------------------------------------------------------------- the backtest
def rule_fired(inputs: dict, out: dict):
    """(name, exposure) of the first fired rule that carries an exposure; informational rules do not set positions."""
    from monitor import rules
    fired = [r for r in rules(inputs, out) if r["fired"]]
    with_expo = [r for r in fired if r.get("exposure") is not None]
    r = with_expo[0] if with_expo else (fired[0] if fired else None)
    return (r["name"], r.get("exposure")) if r else (None, None)


def simulate(points: list[dict], prices: dict, bench: dict, sizing: str = "rules", use_overlays: bool = False, macro: dict | None = None, cfg: dict | None = None) -> dict:
    """Exposure set at the close of each evaluation day (release + lag trading days); cash earns nothing; price returns only."""
    days = sorted(d for d in prices if d >= points[0]["date"])
    expo, equity, bh, spy = 1.0, 1.0, 1.0, 1.0
    first = days[0]
    curve, changes = [], []
    sched = {}
    for p in points:
        sched[p["date"]] = p
    prev = first
    for d in days:
        r = prices[d] / prices[prev] - 1
        equity *= 1 + expo * r
        bh *= 1 + r
        spy *= 1 + (bench[d] / bench[prev] - 1) if d in bench and prev in bench else 1
        if d in sched:
            p = sched[d]
            e = p["ev_exposure"] if sizing == "ev" else p["exposure"]
            if e is None:
                e = expo
            if use_overlays:
                st = overlays.market_state(prices, d, macro or {}, cfg)
                res = overlays.apply(e, st, expo)
                p["overlay"] = {"regime_cap": st["regime_cap"], "vol_scale": st["vol_scale"], "above_sma": st["above_sma"], "stress": st["stress"], "recommended": res["recommended"]}
                e = round(res["recommended"], 2)
            if abs(e - expo) > 1e-9:
                changes.append({"date": d, "from": expo, "to": e, "rule": p["rule"], "price": prices[d]})
                expo = e
        curve.append({"date": d, "strategy": equity, "buy_hold": bh, "spy": spy, "exposure": expo})
        prev = d
    return {"curve": curve, "changes": changes, "final": {"strategy": equity, "buy_hold": bh, "spy": spy}}


def release_evals(ticker: str, data: dict, since: str, lag_days: int = 2) -> list[tuple[str, int]]:
    """(evaluation date, quarter key): the earnings release (8-K item 2.02) plus `lag_days` trading days."""
    rows = get("/api/v1/data/datasets/sec.earnings_releases/rows", limit=200, **{"eq.ticker": ticker})["data"]["rows"]
    releases = sorted({r["filing_date"] for r in rows if r["filing_date"] >= since and r["form"] == "8-K"})
    q_ends = sorted((r["end"], r["key"]) for r in data["kpis"]["revenue"] if r["kind"] == "quarterly")
    days = sorted(data["prices"][ticker])
    out = []
    for rel in releases:
        ended = [k for e, k in q_ends if e < rel]
        if not ended:
            continue
        key = ended[-1]
        after = [d for d in days if d > rel]
        if len(after) < lag_days:
            continue
        out.append((after[lag_days - 1], key))
    seen, dedup = set(), []
    for d, k in out:
        if k not in seen:
            seen.add(k); dedup.append((d, k))
    return dedup


# ------------------------------------------------------------------------------------- reporting
def stats(sim: dict, points: list[dict]) -> dict:
    curve = sim["curve"]
    years = (dt.date.fromisoformat(curve[-1]["date"]) - dt.date.fromisoformat(curve[0]["date"])).days / 365.25
    def cagr(x):
        return x ** (1 / years) - 1 if years > 0 else None
    def maxdd(key):
        peak, worst = 0.0, 0.0
        for c in curve:
            peak = max(peak, c[key]); worst = min(worst, c[key] / peak - 1)
        return worst
    scored = [p for p in points if p.get("price_12m")]
    inside = [p for p in scored if p["bear"] <= p["price_12m"] <= p["bull"]]
    mape = statistics.fmean(abs(p["house"] / p["price_12m"] - 1) for p in scored) if scored else None
    bias = statistics.fmean(p["house"] / p["price_12m"] - 1 for p in scored) if scored else None
    return {"years": years, "final": sim["final"], "cagr": {k: cagr(v) for k, v in sim["final"].items()},
            "max_drawdown": {"strategy": maxdd("strategy"), "buy_hold": maxdd("buy_hold"), "spy": maxdd("spy")},
            "avg_exposure": statistics.fmean(c["exposure"] for c in curve), "trades": len(sim["changes"]),
            "scored_points": len(scored), "within_band": len(inside), "house_mape_12m": mape, "house_bias_12m": bias}


def render_reports(ticker: str, template: dict, since: str, lag: int, results: dict):
    import html as H
    pc = lambda x, d=1, sign=False: "—" if x is None else f"{x * 100:{'+' if sign else ''}.{d}f}%"
    usd = lambda x, d=0: "—" if x is None else f"${x:,.{d}f}"
    names = list(results)
    LABEL = {"momentum_rules": "Momentum street, rules", "guidance_rules": "Guidance street, rules", "guidance_ev": "Guidance street, EV sizing, rate-aware + ROIC anchor",
             "guidance_ev_overlays": "All improvements (+ regime, vol, trend overlays)", "foresight_rules": "Foresight street, rules (upper bound)"}
    st = {v: stats(results[v]["sim"], results[v]["points"]) for v in names}
    ref = st[names[0]]
    first, last = results[names[0]]["sim"]["curve"][0]["date"], results[names[0]]["sim"]["curve"][-1]["date"]
    expo_txt = lambda r: "keep" if r.get("exposure") is None else "%.0f%%" % (r["exposure"] * 100)
    rules_txt = "; ".join("%s → %s" % (r["name"], expo_txt(r)) for r in template["monitor"]["rules"])
    ov = template["blend"].get("overlays", {})
    # ---- markdown
    hdr = "| | " + " | ".join(LABEL.get(v, v) for v in names) + " | Buy & hold | SPY |"
    sep = "|---|" + "---:|" * (len(names) + 2)
    L = [f"# {ticker} backtest — the valuation model as a quarterly position rule", "",
         f"Window {first} → {last}. Decision point: each earnings release (8-K item 2.02) plus {lag} trading days; the position is set at that close. "
         f"Cash earns nothing; price returns only (no dividends, taxes or costs). Scenario assumptions, adjustments and rules are today's `inputs.json`; "
         f"segments are dropped (not in XBRL), so the advertising uplift becomes a total-revenue uplift.", "",
         "Streets (the forecast block, since historical sell-side consensus is not available): **momentum** = TTM growth fading 20%/yr, flat TTM margin and tax, capex on its own TTM growth; "
         "**guidance** = the company's own next-quarter revenue range and full-year capex range from the press release (official 8-K exhibit), fading from there; "
         "**foresight** = reported figures where the forecast periods have since been reported (upper bound). "
         "Sizing: **rules** = the first fired rule's exposure; **EV** = reward-to-risk on the probability-weighted target (p bear/base/bull "
         + "/".join(pc(template["scenarios"][k].get("probability", 0), 0) for k in ("bear", "base", "bull")) + f", full position at {template['blend'].get('sizing', {}).get('full_at_reward_to_risk', 2.0):.1f}x). "
         f"Overlays: regime cap {pc(ov.get('regime', {}).get('cap', 0.5), 0)} when NFCI > {ov.get('regime', {}).get('nfci_max', 0):+.1f}, VIX > {ov.get('regime', {}).get('vix_max', 30):.0f} or Baa spread > {pc(ov.get('regime', {}).get('baa10y_max', 0.025), 1)}; "
         f"vol scaling to {pc(ov.get('vol', {}).get('target', 0.35), 0)} realised (floor {ov.get('vol', {}).get('floor', 0.25)}); increases staged at {pc(ov.get('trend', {}).get('max_step_below', 0.25), 0)} per decision below the {ov.get('trend', {}).get('sma', 200)}-day average.", "",
         "## Result", "", hdr, sep]
    row = lambda label, f: f"| {label} | " + " | ".join(f(st[v]) for v in names) + " | "
    L.append(row("Growth of $1", lambda x: f"{x['final']['strategy']:.2f}x") + f"{ref['final']['buy_hold']:.2f}x | {ref['final']['spy']:.2f}x |")
    L.append(row("CAGR", lambda x: pc(x['cagr']['strategy'])) + f"{pc(ref['cagr']['buy_hold'])} | {pc(ref['cagr']['spy'])} |")
    L.append(row("Max drawdown", lambda x: pc(x['max_drawdown']['strategy'])) + f"{pc(ref['max_drawdown']['buy_hold'])} | {pc(ref['max_drawdown']['spy'])} |")
    L.append(row("Average exposure", lambda x: pc(x['avg_exposure'], 0)) + "100% | 100% |")
    L.append(row("Position changes", lambda x: str(x['trades'])) + "0 | 0 |")
    L.append(row("12m price inside bear–bull band", lambda x: f"{x['within_band']}/{x['scored_points']}") + " | |")
    L.append(row("House target vs 12m price: abs error / bias", lambda x: f"{pc(x['house_mape_12m'], 0)} / {pc(x['house_bias_12m'], 0, True)}") + " | |")
    L += ["", f"Rules (first fired sets the rules position): {rules_txt}.", ""]
    for v in names:
        L += [f"## Quarter by quarter — {LABEL.get(v, v)}", "",
              "| Decision day | Quarter | Price | Bear | Base | Bull | House | Upside | Rule | Rule pos. | EV pos. | Overlay → pos. | Street g | Price implies (pp) | WACC | Price 12m later |",
              "|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---|---:|---:|---:|---:|"]
        for p in results[v]["points"]:
            o = p.get("overlay") or {}
            L.append(f"| {p['date']} | {p['period']} | {usd(p['price'])} | {usd(p['bear'])} | {usd(p['base'])} | {usd(p['bull'])} | **{usd(p['house'])}** | {pc(p['upside'], 0, True)} | {p['rule'] or '—'} | "
                     f"{'keep' if p['exposure'] is None else pc(p['exposure'], 0)} | {pc(p['ev_exposure'], 0)} | "
                     f"{(('cap ' + pc(o['regime_cap'], 0) + ', vol ' + ('%.2f' % o['vol_scale']) + (', below SMA' if o.get('above_sma') is False else '') + ' → ' + pc(o['recommended'], 0)) if o else '—')} | "
                     f"{pc(p['street']['g_ttm'], 0, True)}{' (guid.)' if p['street'].get('guidance_used') else ''} | {('%+.1f' % (p['implied_growth_pp'] * 100)) if p.get('implied_growth_pp') is not None else '—'} | {pc(p['wacc'])} | {usd(p['price_12m']) if p['price_12m'] else '—'} |")
        ch = results[v]["sim"]["changes"]
        L += ["", "Position changes: " + ("; ".join(f"{c['date']} {c['from']:.0%}→{c['to']:.0%} ({c['rule'] or 'EV'}, {usd(c['price'])})" for c in ch) if ch else "none") + ".", ""]
    L += ["## Read this honestly", "",
          "- The streets are mechanical stand-ins for the analyst's consensus block. The guidance street is the best official proxy: the company's own next-quarter revenue and full-year capex ranges.",
          "- EV sizing is continuous, so it trades more often and holds less on average; judge it on return per unit of exposure and on drawdown, not on the raw multiple alone.",
          "- Overlays are blunt: a regime cap and vol scaling cut exposure in stress whether or not the thesis changed. That is the point, and the cost.",
          "- Twelve decisions on one name in one window; do not tune thresholds on this. Run more names and a 2022-style drawdown before trusting a rule change.",
          "- Price returns only, cash at zero, no costs; today's scenario assumptions on every past date; segments dropped.", "",
          f"_Generated {dt.date.today().isoformat()} by the stock-evaluation skill (scripts/backtest.py); data: SEC XBRL, 8-K exhibits, FRED (DGS10, NFCI, VIXCLS, BAA10Y), Alpaca bars through atlas._"]
    md = "\n".join(L)
    # ---- html
    payload = json.dumps({"names": names, "labels": {v: LABEL.get(v, v) for v in names},
                          "curves": {v: results[v]["sim"]["curve"] for v in names},
                          "points": {v: [{k: p.get(k) for k in ("date", "period", "price", "bear", "base", "bull", "house", "rule", "price_12m")} for p in results[v]["points"]] for v in names}})
    sum_rows = "".join(f"<tr><td>{lbl}</td>" + "".join(f"<td>{f(st[v])}</td>" for v in names) + f"<td>{bh}</td><td>{spy}</td></tr>" for lbl, f, bh, spy in [
        ("Growth of $1", lambda x: f"{x['final']['strategy']:.2f}x", f"{ref['final']['buy_hold']:.2f}x", f"{ref['final']['spy']:.2f}x"),
        ("CAGR", lambda x: pc(x['cagr']['strategy']), pc(ref['cagr']['buy_hold']), pc(ref['cagr']['spy'])),
        ("Max drawdown", lambda x: pc(x['max_drawdown']['strategy']), pc(ref['max_drawdown']['buy_hold']), pc(ref['max_drawdown']['spy'])),
        ("Average exposure / changes", lambda x: f"{pc(x['avg_exposure'], 0)} / {x['trades']}", "100% / 0", "100% / 0"),
        ("12m price inside bear–bull band", lambda x: f"{x['within_band']}/{x['scored_points']}", "", ""),
        ("House target vs 12m price: abs error / bias", lambda x: f"{pc(x['house_mape_12m'], 0)} / {pc(x['house_bias_12m'], 0, True)}", "", "")])
    summary = "<table class='sum'><thead><tr><th></th>" + "".join(f"<th>{H.escape(LABEL.get(v, v))}</th>" for v in names) + "<th>Buy &amp; hold</th><th>SPY</th></tr></thead><tbody>" + sum_rows + "</tbody></table>"
    tables = ""
    for v in names:
        rows = ""
        for p in results[v]["points"]:
            o = p.get("overlay") or {}
            rows += (f"<tr><td>{p['date']}</td><td>{p['period']}</td><td class='n'>{usd(p['price'])}</td><td class='n'>{usd(p['bear'])}</td><td class='n'>{usd(p['base'])}</td><td class='n'>{usd(p['bull'])}</td>"
                     f"<td class='n'><b>{usd(p['house'])}</b></td><td class='n'>{pc(p['upside'], 0, True)}</td><td>{H.escape(p['rule'] or '—')}</td><td class='n'>{'keep' if p['exposure'] is None else pc(p['exposure'], 0)}</td><td class='n'>{pc(p['ev_exposure'], 0)}</td>"
                     f"<td>{(('cap ' + pc(o['regime_cap'], 0) + ', vol ' + ('%.2f' % o['vol_scale']) + (', below SMA' if o.get('above_sma') is False else '') + ' → ' + pc(o['recommended'], 0)) if o else '—')}</td>"
                     f"<td class='n'>{pc(p['street']['g_ttm'], 0, True)}{' (g)' if p['street'].get('guidance_used') else ''}</td><td class='n'>{('%+.1f' % (p['implied_growth_pp'] * 100)) if p.get('implied_growth_pp') is not None else '—'}</td><td class='n'>{pc(p['wacc'])}</td><td class='n'>{usd(p['price_12m']) if p['price_12m'] else '—'}</td></tr>")
        tables += f"<h3>{H.escape(LABEL.get(v, v))}</h3><div class='tbl'><table><thead><tr><th>Decision day</th><th>Quarter</th><th>Price</th><th>Bear</th><th>Base</th><th>Bull</th><th>House</th><th>Upside</th><th>Rule</th><th>Rule pos.</th><th>EV pos.</th><th>Overlay → pos.</th><th>Street g</th><th>Price implies (pp)</th><th>WACC</th><th>Price 12m later</th></tr></thead><tbody>{rows}</tbody></table></div>"
    rules_html = "".join("<li><b>%s</b> → %s — %s <code>%s</code></li>" % (H.escape(r["name"]), expo_txt(r), H.escape(r["action"]), H.escape(r["when"])) for r in template["monitor"]["rules"])
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{ticker} backtest</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>:root{{color-scheme:light dark;--bg:#fcfcfb;--bg2:#f1f0ec;--tx:#0b0b0b;--t2:#52514e;--line:#dcdad4}}@media(prefers-color-scheme:dark){{:root{{--bg:#1a1a19;--bg2:#242422;--tx:#f0efec;--t2:#c3c2b7;--line:#3a3936}}}}
body{{margin:0;background:var(--bg);color:var(--tx);font:15px/1.55 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif}}main{{max-width:1240px;margin:0 auto;padding:24px 16px 48px}}h1{{font-size:24px;margin:0 0 6px}}h2{{font-size:18px;margin:32px 0 8px}}h3{{font-size:15px;margin:22px 0 6px;color:var(--t2)}}
p.sub{{color:var(--t2)}}table{{border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}}th,td{{padding:5px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}th:first-child,td:first-child{{text-align:left}}thead th{{background:var(--bg2);color:var(--t2);font-weight:600}}
.sum{{width:100%;margin:8px 0 16px}}.sum td:first-child{{text-align:left}}.tbl{{overflow-x:auto;border:1px solid var(--line);border-radius:8px;margin:8px 0 16px}}.tbl table{{width:100%}}.chart{{height:380px;margin:8px 0}}ul{{padding-left:20px}}footer{{color:var(--t2);font-size:12px;margin-top:32px}}</style></head><body><main>
<h1>{ticker} — the valuation model as a quarterly position rule, {first} → {last}</h1>
<p class="sub">Decision point: each earnings release plus {lag} trading days; the position is set at that close. Price returns only, cash at zero. Streets: <b>momentum</b> (no look-ahead extrapolation), <b>guidance</b> (the company's own next-quarter revenue and full-year capex ranges from the 8-K exhibit), <b>foresight</b> (reported figures, an upper bound). Sizing: <b>rules</b> or <b>EV</b> (reward to risk on the probability-weighted target). Overlays: regime cap, volatility scaling, trend staging.</p>
{summary}
<div id="c_eq" class="chart"></div>
<div id="c_tgt" class="chart"></div>
<h2>Rules</h2><ul>{rules_html}</ul>
<h2>Quarter by quarter</h2>{tables}
<h2>Read this honestly</h2><ul>
<li>The streets are mechanical stand-ins for the analyst's consensus block; the guidance street is the best official proxy.</li>
<li>EV sizing is continuous and holds less on average; judge it on return per unit of exposure and on drawdown, not the raw multiple alone. Overlays cut exposure in stress whether or not the thesis changed.</li>
<li>Twelve decisions on one name in one window; do not tune thresholds on this. No dividends, taxes or costs; today's assumptions on every past date; segments dropped.</li></ul>
<footer>Generated {dt.date.today().isoformat()} by the stock-evaluation skill (scripts/backtest.py). Data: SEC XBRL, 8-K exhibits, FRED (DGS10, NFCI, VIXCLS, BAA10Y), Alpaca bars through atlas.</footer></main>
<script>
const D={payload};const dark=matchMedia('(prefers-color-scheme: dark)').matches;
const C={{s1:dark?'#3987e5':'#2a78d6',s2:dark?'#d95926':'#eb6834',s3:dark?'#199e70':'#1baf7a',s4:dark?'#c98500':'#eda100',s5:dark?'#d55181':'#e87ba4',tx:dark?'#f0efec':'#0b0b0b',t2:dark?'#c3c2b7':'#52514e',grid:dark?'#3a3936':'#e6e4de'}};
const base={{paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{{color:C.t2,size:12}},margin:{{l:56,r:16,t:40,b:40}},legend:{{orientation:'h',y:-0.18}}}};
const cols=[C.s1,C.s4,C.s5,C.s3,C.t2];const c0=D.curves[D.names[0]];
const traces=[{{x:c0.map(c=>c.date),y:c0.map(c=>c.buy_hold),name:'Buy & hold',line:{{color:C.tx,width:2}}}}];
D.names.forEach((n,i)=>{{const c=D.curves[n];traces.push({{x:c.map(x=>x.date),y:c.map(x=>x.strategy),name:D.labels[n],line:{{color:cols[i%cols.length],width:n==='guidance_ev_overlays'?2.5:1.5,dash:n==='foresight_rules'?'dot':'solid'}}}});}});
traces.push({{x:c0.map(c=>c.date),y:c0.map(c=>c.spy),name:'SPY',line:{{color:C.s2,width:1.5,dash:'dashdot'}}}});
const ce=D.curves['guidance_ev_overlays']||c0;
traces.push({{x:ce.map(c=>c.date),y:ce.map(c=>c.exposure),name:'Exposure (all improvements)',yaxis:'y2',line:{{color:C.s3,width:1,shape:'hv'}},fill:'tozeroy',fillcolor:'rgba(27,175,122,0.08)',showlegend:false,hovertemplate:'%{{x}} exposure %{{y:.0%}}<extra></extra>'}});
Plotly.newPlot('c_eq',traces,{{...base,title:{{text:'Growth of $1 (price return); shaded = exposure of the all-improvements variant',font:{{size:14,color:C.tx}},x:0}},yaxis:{{gridcolor:C.grid,tickprefix:'$'}},yaxis2:{{overlaying:'y',side:'right',range:[0,4],showgrid:false,showticklabels:false}},xaxis:{{showgrid:false}}}},{{displayModeBar:false,responsive:true}});
const pm=D.points['guidance_ev']||D.points[D.names[0]];const p0=D.points[D.names[0]];
Plotly.newPlot('c_tgt',[
 {{x:c0.map(c=>c.date),y:c0.map(c=>c.buy_hold*p0[0].price),name:'Price',line:{{color:C.t2,width:1.5}},hovertemplate:'%{{x}} $%{{y:,.0f}}<extra></extra>'}},
 {{x:p0.map(p=>p.date),y:p0.map(p=>p.house),name:'House target, momentum street',mode:'markers',marker:{{color:C.s1,size:8,symbol:'diamond'}},hovertemplate:'%{{x}} $%{{y:,.0f}}<extra></extra>'}},
 {{x:pm.map(p=>p.date),y:pm.map(p=>p.house),name:'House target, guidance street (bar = bear to bull)',mode:'markers',marker:{{color:C.s3,size:9}},error_y:{{type:'data',symmetric:false,array:pm.map(p=>p.bull-p.house),arrayminus:pm.map(p=>p.house-p.bear),color:C.s3,thickness:1.2}},hovertemplate:'%{{x}} $%{{y:,.0f}}<extra></extra>'}},
 {{x:D.points.foresight_rules.map(p=>p.date),y:D.points.foresight_rules.map(p=>p.house),name:'House target, foresight street',mode:'markers',marker:{{color:C.s4,size:7,symbol:'square'}},hovertemplate:'%{{x}} $%{{y:,.0f}}<extra></extra>'}}],
 {{...base,title:{{text:'12-month house target on each decision day against the price path',font:{{size:14,color:C.tx}},x:0}},yaxis:{{gridcolor:C.grid,tickprefix:'$'}},xaxis:{{showgrid:false}}}},{{displayModeBar:false,responsive:true}});
</script></body></html>"""
    return md, html


def main(argv: list[str]) -> int:
    folder = os.path.abspath(argv[argv.index("--dir") + 1]) if "--dir" in argv else os.getcwd()
    since = argv[argv.index("--since") + 1] if "--since" in argv else (dt.date.today() - dt.timedelta(days=3 * 365)).isoformat()
    out_dir = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(folder, "backtest")
    os.makedirs(out_dir, exist_ok=True)
    template = mm.load(os.path.join(folder, "inputs.json"))
    ticker = template["company"]["ticker"]
    data = fetch_all(ticker, folder, since)
    evals = release_evals(ticker, data, since, lag_days=int(argv[argv.index("--lag")+1]) if "--lag" in argv else 2)
    results = {}
    cache = {}
    for vname, (street, sizing, use_ov, improvements) in VARIANTS.items():
        pts = []
        for filed, key in evals:
            ck = (street, improvements, key)
            if ck not in cache:
                inp = build_inputs(template, data, key, filed, street, improvements)
                cache[ck] = (inp, mm.Model(inp).run())
            inp, out = cache[ck]
            s, h = out["scenarios"], out["house"]
            fwd_date = (dt.date.fromisoformat(filed) + dt.timedelta(days=365)).isoformat()
            fwd_px = last_on_or_before(data["prices"][ticker], fwd_date) if fwd_date <= max(data["prices"][ticker]) else None
            pts.append({"date": filed, "period": f"FY{key // 10} Q{key % 10}", "price": inp["market"]["price"],
                        "bear": s["bear"]["blended_target"], "base": s["base"]["blended_target"], "bull": s["bull"]["blended_target"],
                        "house": h["target"], "upside": h["upside"], "rule": rule_fired(inp, out)[0], "exposure": rule_fired(inp, out)[1],
                        "ev_exposure": out.get("expected", {}).get("exposure"), "expected_target": out.get("expected", {}).get("expected_target"),
                        "implied_growth_pp": (out.get("implied") or {}).get("growth_pp"),
                        "wacc": out["wacc"]["wacc"], "rf": inp["wacc"]["risk_free"], "beta": inp["wacc"]["beta"],
                        "street": inp["_street"], "price_12m": fwd_px,
                        "checks_failed": [c["check"] for c in out["checks"] if not c["ok"] and not c.get("warn_only")],
                        "q5_q8_eps": s["base"]["multiples"]["q5_q8_eps"], "pe_at_price": s["base"]["multiples"]["price_implied_multiple"]})
        sim = simulate(pts, data["prices"][ticker], data["prices"]["SPY"], sizing, use_ov, data["macro"], template["blend"].get("overlays"))
        results[vname] = {"points": pts, "sim": sim, "street": street, "sizing": sizing, "overlays": use_ov, "improvements": improvements}
    lag = int(argv[argv.index("--lag") + 1]) if "--lag" in argv else 2
    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump({"ticker": ticker, "since": since, "generated": dt.date.today().isoformat(), "lag_days": lag, "results": results}, fh, indent=1, default=str)
    md, html = render_reports(ticker, template, since, lag, results)
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(os.path.join(out_dir, "report.html"), "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"[written {out_dir}/results.json, report.md, report.html]", file=sys.stderr)
    print(json.dumps({v: results[v]["sim"]["final"] for v in results}, indent=1))
    for v in results:
        print(f"\n== {v}")
        for p in results[v]["points"]:
            ov = p.get("overlay") or {}
            print(f"{p['date']} {p['period']:<10} px {p['price']:>5.0f}  b/b/b {p['bear']:>4.0f}/{p['base']:>4.0f}/{p['bull']:>4.0f} house {p['house']:>4.0f} ({p['upside']:+.0%}) "
                  f"{(p['rule'] or '-')[:16]:<16} rule {('%.0f%%' % (p['exposure'] * 100)) if p['exposure'] is not None else 'keep':>5} ev {p['ev_exposure']:.0%} "
                  f"{('ov ' + ('%.0f%%' % (ov['recommended'] * 100)) + (' stress' if ov.get('stress') else '')) if ov else '':<14} g {p['street']['g_ttm']:+.0%} 12m {p['price_12m'] or 0:>4.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
