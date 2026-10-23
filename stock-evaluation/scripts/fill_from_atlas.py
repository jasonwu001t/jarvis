"""Fill a ticker folder's inputs.json from official sources: XBRL actuals, balance-sheet composites, segments from the
press releases (when the folder has segments.py), and a mechanical "street" for the forecast periods built from the
company's own guidance (next-quarter revenue and, where guided, operating income), beat-adjusted, fading to trend.

  python3 fill_from_atlas.py --dir research/AMZN [--since-fy 2023] [--fade 0.8]

Keeps everything the analyst sets (scenarios, adjustments, rules, thesis, blend settings, wacc.erp); replaces periods,
lines, segments, as_of and the price. The consensus block it writes is labelled as a guidance street in
as_of.consensus_source: replace it with real sell-side consensus when you have it. Balance-sheet mapping
(inputs.balance_mapping): investments = the listed XBRL concepts; debt adds finance-lease liabilities (10-K only,
carried forward); cash adds marketable securities.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import statistics
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guidance as guid  # noqa: E402
from monitor import KPI_TO_LINE, PER_SHARE, period_key  # noqa: E402

ATLAS = os.environ.get("ATLAS_URL", "http://127.0.0.1:8000").rstrip("/")
DEFAULT_INVESTMENT_CONCEPTS = ["EquityMethodInvestments", "EquitySecuritiesWithoutReadilyDeterminableFairValueAmount"]


def get(path: str, **params) -> dict:
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    with urllib.request.urlopen(urllib.request.Request(f"{ATLAS}{path}?{qs}", headers={"Accept": "application/json"}), timeout=120) as r:
        return json.load(r)


def kpis(ticker: str) -> dict:
    out = {}
    for k in get(f"/api/v1/filings/ticker/{ticker}", top_n=1)["data"]["xbrl"]["kpis"]:
        out[k["id"]] = {}
        for r in k.get("quarterly", []) + k.get("annual", []):
            if r["value"] is None:
                continue
            try:
                key = period_key(r["period"])     # a balance on no fiscal period is labelled by its date: skipped
            except ValueError:
                continue
            out[k["id"]][key] = {"value": r["value"] if k["id"] in PER_SHARE else r["value"] / 1e6, "end": r["end"]}
    return out


def facts(ticker: str, concept: str, since: str) -> dict:
    rows = get("/api/v1/data/datasets/sec.company_facts/rows", start=since, limit=500, **{"eq.ticker": ticker, "eq.metric": concept})["data"]["rows"]
    out = {}
    for r in rows:
        if r.get("period_start") is None and r["value"] is not None:
            out[r["period_end"]] = r["value"] / 1e6
    return out


def latest_at(series: dict, end: str):
    ks = [k for k in series if k <= end]
    return series[max(ks)] if ks else 0.0


def main(argv: list[str]) -> int:
    folder = os.path.abspath(argv[argv.index("--dir") + 1]) if "--dir" in argv else os.getcwd()
    since_fy = int(argv[argv.index("--since-fy") + 1]) if "--since-fy" in argv else dt.date.today().year - 3
    fade = float(argv[argv.index("--fade") + 1]) if "--fade" in argv else 0.8
    cfade = float(argv[argv.index("--capex-fade") + 1]) if "--capex-fade" in argv else None   # growth mode: capex growth fades at this rate
    # default intensity mode: capex / revenue held at the current year's level in FY+1, eased by --capex-ease in FY+2 (0.85 = 15% lower intensity)
    cease = float(argv[argv.index("--capex-ease") + 1]) if "--capex-ease" in argv else 0.85
    path = os.path.join(folder, "inputs.json")
    inp = json.load(open(path, encoding="utf-8"))
    ticker = inp["company"].get("filing_ticker") or inp["company"]["ticker"]   # SEC data ticker (GOOG -> GOOGL)
    K = kpis(ticker)
    rev = K["revenue"]
    qkeys = sorted(k for k in rev if k % 10 != 0)
    latest = qkeys[-1]
    fy, q = latest // 10, latest % 10
    since = f"{since_fy - 1}-01-01"
    # ---- actual lines
    L = {}
    for kpi, line in KPI_TO_LINE.items():
        if line in ("cash", "total_debt", "gaap_eps"):
            continue
        L[line] = {k: v["value"] for k, v in K.get(kpi, {}).items() if k // 10 >= since_fy - 1}
    ends = {k: v["end"] for k, v in rev.items()}
    bm = inp.get("balance_mapping") or {}
    ms = facts(ticker, "MarketableSecuritiesCurrent", since)
    fl = facts(ticker, "FinanceLeaseLiability", since)
    inv = {c: facts(ticker, c, since) for c in bm.get("investment_concepts", DEFAULT_INVESTMENT_CONCEPTS)}
    cash = {k: v["value"] for k, v in K["cash"].items()}
    debt = {k: v["value"] for k, v in K["total_debt"].items()}
    L["cash_and_st_investments"] = {k: cash[k] + latest_at(ms, ends[k]) for k in cash if k in ends and k // 10 >= since_fy - 1}
    L["debt"] = {k: debt[k] + latest_at(fl, ends[k]) for k in debt if k in ends and k // 10 >= since_fy - 1}
    L["investments"] = {k: sum(latest_at(s, ends[k]) for s in inv.values()) for k in ends if k // 10 >= since_fy - 1 and k in cash}
    L["minority_interest"] = {k: 0.0 for k in L["investments"]}
    L["other_income"] = {k: L["pretax_income"][k] - L["operating_income"][k] for k in L["pretax_income"] if k in L["operating_income"]}
    L["adjustments"] = {k: 0.0 for k in L["net_income"]}
    L["adjusted_net_income"] = dict(L["net_income"])
    # working-capital increase derived from the cash-flow statement: (NOPAT + D&A + SBC) − operating cash flow, where
    # NOPAT = operating income x (1 − effective tax); non-operating gains (equity marks) are excluded that way
    def _nopat(k):
        pre, tx = L["pretax_income"].get(k, 0.0), L["income_tax"].get(k, 0.0)
        rate = tx / pre if pre > 0 else 0.2
        rate = rate if 0 <= rate <= 0.5 else 0.2
        return L["operating_income"][k] * (1 - rate)
    L["wc_increase"] = {k: (_nopat(k) + L["d_and_a"].get(k, 0.0) + L["sbc"].get(k, 0.0)) - L["operating_cash_flow"][k]
                        for k in L["operating_cash_flow"] if k in L["operating_income"]}
    for name in ("dps", "dividends_total", "buybacks", "finance_lease_additions"):
        L.setdefault(name, {})
    # ---- segments from the press releases, when the folder provides segments.py
    seg_defs = {}
    seg_mod = None
    if os.path.exists(os.path.join(folder, "segments.py")):
        spec = importlib.util.spec_from_file_location("ticker_segments", os.path.join(folder, "segments.py"))
        seg_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(seg_mod)
        seg_defs = getattr(seg_mod, "DEFINITIONS", {})
    releases = guid.collect(ticker, folder, since=f"{since_fy - 1}-01-01")
    if seg_mod:
        q_ends = sorted((v["end"], k) for k, v in rev.items() if k % 10 != 0)
        for r in releases:
            text_path = os.path.join(folder, "source", "exhibits", f"{r['accession']}-ex991.txt")
            if not os.path.exists(text_path):
                continue
            ended = [k for e, k in q_ends if e < r["date"]]
            if not ended:
                continue
            key = ended[-1]
            for name, vals in seg_mod.extract(open(text_path, encoding="utf-8").read()).items():
                if "revenue" in vals:
                    L.setdefault(f"seg:{name}", {})[key] = vals["revenue"]
                if "oi" in vals:
                    L.setdefault(f"segoi:{name}", {})[key] = vals["oi"]
        for name in seg_defs:
            for line in (f"seg:{name}", f"segoi:{name}"):
                d = L.get(line, {})
                for y in range(since_fy, fy + 1):
                    if all((y * 10 + i) in d for i in range(1, 5)):
                        d[y * 10] = sum(d[y * 10 + i] for i in range(1, 5))
    # ---- the street
    last4, prev4 = qkeys[-4:], qkeys[-8:-4]
    ttm = lambda line, ks: sum(L[line].get(k, 0.0) for k in ks)
    g_ttm = ttm("revenue", last4) / ttm("revenue", prev4) - 1
    g_capex = ttm("capex", last4) / ttm("capex", prev4) - 1 if ttm("capex", prev4) else g_ttm
    margin = ttm("operating_income", last4) / ttm("revenue", last4)
    pre = ttm("pretax_income", last4)
    tax = min(0.30, max(0.10, ttm("income_tax", last4) / pre)) if pre > 0 else 0.15
    ratio = lambda line: ttm(line, last4) / ttm("revenue", last4)
    da_r, sbc_r, wc_r = ratio("d_and_a"), ratio("sbc"), ratio("wc_increase")
    lease_r = ttm("finance_lease_additions", last4) / ttm("capex", last4) if ttm("capex", last4) else 0.0
    shares = L["diluted_shares"].get(latest) or L["diluted_shares"][max(L["diluted_shares"])]
    dps_q = L["dps"].get(latest, 0.0)
    gd = next((r for r in reversed(releases) if r.get("revenue_next_quarter") and r["revenue_next_quarter"]["period_key"] > latest), None)
    beats = []
    oi_beats = []
    for r in releases:
        rv = r.get("revenue_next_quarter")
        if rv and rv["period_key"] in rev and rv["period_key"] <= latest:
            beats.append(rev[rv["period_key"]]["value"] / rv["mid"])
        oi = r.get("operating_income_next_quarter")
        if oi and oi["period_key"] in L["operating_income"] and oi["period_key"] <= latest:
            oi_beats.append(L["operating_income"][oi["period_key"]] / oi["mid"])
    beat = statistics.fmean(beats[-6:]) if beats else 1.0
    oi_beat = statistics.fmean(oi_beats[-6:]) if oi_beats else 1.0
    g = g_ttm
    if gd:
        prior = L["revenue"].get(gd["revenue_next_quarter"]["period_key"] - 10)
        if prior:
            g = gd["revenue_next_quarter"]["mid"] * beat / prior - 1
    rq = [fy * 10 + i for i in range(q + 1, 5)]
    fy0, y1, y2 = fy * 10, (fy + 1) * 10, (fy + 2) * 10
    seg_g = {name: (ttm(f"seg:{name}", last4) / ttm(f"seg:{name}", prev4) - 1) if ttm(f"seg:{name}", prev4) else g for name in seg_defs}
    seg_m = {name: (ttm(f"segoi:{name}", last4) / ttm(f"seg:{name}", last4)) if ttm(f"seg:{name}", last4) else 0.0 for name in seg_defs}

    def put(k, revenue, capex, oi=None, g_seg_scale=1.0):
        oi = revenue * margin if oi is None else oi
        ni = oi * (1 - tax)
        vals = {"revenue": revenue, "operating_income": oi, "pretax_income": oi, "income_tax": oi * tax, "net_income": ni, "adjustments": 0.0,
                "adjusted_net_income": ni, "diluted_shares": shares, "dps": dps_q * (4 if k % 10 == 0 else 1), "dividends_total": dps_q * shares * (4 if k % 10 == 0 else 1),
                "d_and_a": revenue * da_r, "sbc": revenue * sbc_r, "wc_increase": revenue * wc_r, "capex": capex, "finance_lease_additions": capex * lease_r,
                "other_income": 0.0, "buybacks": 0.0}
        for line, v in vals.items():
            L.setdefault(line, {})[k] = v

    for k in rq:
        prior = L["revenue"].get(k - 10, L["revenue"][last4[-1]])
        rev_k = prior * (1 + g)
        oi_k = None
        if gd and k == gd["revenue_next_quarter"]["period_key"]:
            rev_k = gd["revenue_next_quarter"]["mid"] * beat
            if gd.get("operating_income_next_quarter"):
                oi_k = gd["operating_income_next_quarter"]["mid"] * oi_beat
        put(k, rev_k, L["capex"].get(k - 10, L["capex"][last4[-1]]) * (1 + g_capex), oi_k)
        for name in seg_defs:
            p_ = L.get(f"seg:{name}", {}).get(k - 10)
            if p_:
                L[f"seg:{name}"][k] = p_ * (1 + seg_g[name] + (g - g_ttm))
                L.setdefault(f"segoi:{name}", {})[k] = L[f"seg:{name}"][k] * seg_m[name]
    put(fy0, sum(L["revenue"][fy * 10 + i] for i in range(1, 5)), sum(L["capex"][fy * 10 + i] for i in range(1, 5)), sum(L["operating_income"][fy * 10 + i] for i in range(1, 5)))
    m_fwd = L["operating_income"][fy0] / L["revenue"][fy0]      # the current year's margin (actual quarters + guided quarter) carries forward
    rev1, rev2 = L["revenue"][fy0] * (1 + g * fade), L["revenue"][fy0] * (1 + g * fade) * (1 + g * fade * fade)
    if cfade is not None:
        cap1, cap2 = L["capex"][fy0] * (1 + g_capex * cfade), L["capex"][fy0] * (1 + g_capex * cfade) * (1 + g_capex * cfade * cfade)
    else:
        inten = L["capex"][fy0] / L["revenue"][fy0]
        cap1, cap2 = rev1 * inten, rev2 * inten * cease
    put(y1, rev1, cap1, rev1 * m_fwd)
    put(y2, rev2, cap2, rev2 * m_fwd)
    for name in seg_defs:
        d = L.get(f"seg:{name}", {})
        if all((fy * 10 + i) in d for i in range(1, 5)):
            d[fy0] = sum(d[fy * 10 + i] for i in range(1, 5))
            L[f"segoi:{name}"][fy0] = sum(L[f"segoi:{name}"].get(fy * 10 + i, 0.0) for i in range(1, 5))
            for yk, f_ in ((y1, fade), (y2, fade * fade)):
                prev = d[yk - 10]
                d[yk] = prev * (1 + seg_g[name] * f_)
                L[f"segoi:{name}"][yk] = d[yk] * seg_m[name]
    # balance items for the street: carry the latest actuals (bridge uses the latest reported quarter anyway)
    for line in ("cash_and_st_investments", "debt", "investments", "minority_interest", "equity"):
        have = sorted(k for k in L.get(line, {}) if k <= latest)
        carry = L[line][have[-1]] if have else 0.0      # some filers lack a recent value (e.g. no debt): carry the last one, else 0
        L.setdefault(line, {})
        for k in [fy0, y1, y2]:
            L[line][k] = carry
    # ---- periods and metadata
    periods = [{"key": k, "year": k // 10, "q": k % 10, "status": "actual"} for k in sorted(set(L["revenue"]) & set(rev)) if k <= latest and k // 10 >= since_fy and (k % 10 != 0 or k // 10 < fy or q == 4)]
    periods += [{"key": k, "year": k // 10, "q": k % 10, "status": "consensus"} for k in rq + [fy0, y1, y2]]
    inp["periods"] = periods
    inp["lines"] = {line: {str(k): round(v, 6) for k, v in vals.items() if k // 10 >= since_fy - 1} for line, vals in L.items()}
    inp["segments"] = seg_defs
    px = get(f"/api/v1/market/prices/{inp['company']['ticker']}", limit=1)["data"]["rows"][0]
    inp["market"].update({"price": float(px["close"]), "price_date": px["as_of_date"], "market_cap_musd_override": None})
    inp["as_of"].update({"latest_reported_fy": fy, "latest_reported_q": q, "balance_sheet_date": rev[latest]["end"],
                         "consensus_date": dt.date.today().isoformat(),
                         "consensus_source": (f"Guidance street built by fill_from_atlas.py on {dt.date.today()}: next-quarter revenue"
                                              + (" and operating income" if gd and gd.get("operating_income_next_quarter") else "")
                                              + f" from the {gd['date']} press release (beat-adjusted x{beat:.3f}" + (f", OI x{oi_beat:.3f}" if oi_beats else "") + ")" if gd else "momentum street")
                                             + f"; growth {g:+.1%} fading {fade:.0%}/yr; TTM margin {margin:.1%}, tax {tax:.1%}; capex {('growth %+.1f%% fading %.0f%%/yr' % (g_capex * 100, cfade * 100)) if cfade is not None else ('intensity held at %.1f%% of revenue in FY+1, x%.2f in FY+2' % (L['capex'][fy0] / L['revenue'][fy0] * 100, cease))}; working capital derived as NOPAT + D&A + SBC − OCF. Replace with sell-side consensus when available."})
    inp["_street"] = {"g": g, "g_ttm": g_ttm, "g_capex": g_capex, "margin_ttm": margin, "tax_ttm": tax, "beat": beat, "oi_beat": oi_beat, "da_ratio": da_r, "sbc_ratio": sbc_r, "wc_ratio": wc_r,
                      "segment_growth": seg_g, "segment_margin": seg_m, "guidance_release": gd["date"] if gd else None}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(inp, fh, indent=1, ensure_ascii=False)
    print(json.dumps({"latest": latest, "price": inp["market"]["price"], "street": inp["_street"], "periods": len(periods), "segments": list(seg_defs)}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
