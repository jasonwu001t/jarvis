"""Fill a ticker folder's inputs.json from official sources through atlas: XBRL actuals (US GAAP or IFRS, in USD, per
listed share), balance-sheet composites, business segments from the XBRL segment facts, and a mechanical "street" for
the forecast periods built from the company's own guidance (sec.earnings_guidance: next-quarter revenue and, where
guided, operating income), beat-adjusted, fading to trend. No per-company code: a folder's segments.py and guidance.py's
regexes are fallbacks only, used when atlas has nothing for the ticker, and the fill says so.

  python3 fill_from_atlas.py --dir research/AMZN [--since-fy 2023] [--fade 0.8] [--no-atlas-segments] [--no-atlas-guidance]

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
import atlas_data  # noqa: E402
from monitor import KPI_TO_LINE, PER_SHARE, period_key  # noqa: E402

ATLAS = os.environ.get("ATLAS_URL", "http://127.0.0.1:8000").rstrip("/")
DEFAULT_INVESTMENT_CONCEPTS = ["EquityMethodInvestments", "EquitySecuritiesWithoutReadilyDeterminableFairValueAmount"]


def get(path: str, **params) -> dict:
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    with urllib.request.urlopen(urllib.request.Request(f"{ATLAS}{path}?{qs}", headers={"Accept": "application/json"}), timeout=120) as r:
        return json.load(r)


def kpis(ticker: str) -> dict:
    """KPI series in USD millions, per listed share, from /research/fundamentals (IFRS filers converted by atlas)."""
    return atlas_data.fundamentals(ticker, currency="USD")


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


INTEREST_INCOME_CONCEPTS = ["InvestmentIncomeInterest", "InterestIncomeOther", "InvestmentIncomeInterestAndDividend",
                            "InterestAndOtherIncome", "InterestIncomeOperating",
                            "InvestmentIncomeNet"]   # last: interest plus other investment income (MU, MSFT tag only this)


def quarterly_flows(ticker: str, concept: str, ends: dict, since: str) -> dict:
    """{quarter key: USD m} for a flow concept from sec.company_facts: the 3-month value where filed, Q4 as the fiscal
    year less Q1-Q3 (10-Ks state the year only)."""
    rows = get("/api/v1/data/datasets/sec.company_facts/rows", start=since, limit=2000, **{"eq.ticker": ticker, "eq.metric": concept})["data"]["rows"]
    qtr, yr = {}, {}
    for r in rows:
        if not r.get("period_start") or r.get("value") is None:
            continue
        days = (dt.date.fromisoformat(r["period_end"]) - dt.date.fromisoformat(r["period_start"])).days
        if 80 <= days <= 100:
            qtr[r["period_end"]] = r["value"] / 1e6
        elif 350 <= days <= 380:
            yr[r["period_end"]] = r["value"] / 1e6
    out = {k: qtr[e] for k, e in ends.items() if k % 10 and e in qtr}
    for k, e in ends.items():
        if k % 10 == 4 and k not in out and e in yr and all(k - i in out for i in (1, 2, 3)):
            out[k] = yr[e] - sum(out[k - i] for i in (1, 2, 3))
    return out


def street_other_income(ticker: str, L: dict, K: dict, last4: list, ends: dict, since: str, cash: float, debt: float) -> dict:
    """Forecast other income a year: the last four quarters' interest income as a yield on the average cash and
    investments, applied to the cash the street carries, less interest expense at its TTM rate on the carried debt.
    Without an interest-income fact: the TTM non-operating line (pretax − operating income), said so."""
    avg = lambda line: statistics.fmean(L[line][k] for k in last4 if k in L.get(line, {})) if any(k in L.get(line, {}) for k in last4) else 0.0
    cash_avg, debt_avg = avg("cash_and_st_investments"), avg("debt")
    inc = concept = None
    for c in INTEREST_INCOME_CONCEPTS:
        try:
            fl = quarterly_flows(ticker, c, ends, since)
        except Exception:  # noqa: BLE001 - try the next concept
            continue
        if all(k in fl for k in last4):
            inc, concept = sum(fl[k] for k in last4), c
            break
    ie = K.get("interest_expense", {})
    exp = sum(ie[k]["value"] for k in last4) if all(ie.get(k, {}).get("value") is not None for k in last4) else None
    out = {"interest_income_ttm": inc, "interest_expense_ttm": exp, "cash_yield": None, "debt_rate": None}
    if inc is not None and cash_avg > 0:
        out["cash_yield"] = inc / cash_avg
        annual = out["cash_yield"] * cash
        src = f"interest income ({concept}) {inc:,.0f} over the last four quarters = {out['cash_yield']:.2%} of average cash and investments, on {cash:,.0f} carried"
        if exp is not None and debt_avg > 0:
            out["debt_rate"] = exp / debt_avg
            annual -= out["debt_rate"] * debt
            src += f", less interest expense {exp:,.0f} = {out['debt_rate']:.2%} of average debt, on {debt:,.0f} carried"
    else:
        annual = sum(L["other_income"].get(k, 0.0) for k in last4)
        src = "no interest-income fact in sec.company_facts: TTM non-operating income (pretax − operating income) carried"
    out.update({"annual": annual, "source": src})
    return out


def main(argv: list[str]) -> int:
    folder = os.path.abspath(argv[argv.index("--dir") + 1]) if "--dir" in argv else os.getcwd()
    since_fy = int(argv[argv.index("--since-fy") + 1]) if "--since-fy" in argv else dt.date.today().year - 3
    fade = float(argv[argv.index("--fade") + 1]) if "--fade" in argv else 0.8
    cfade = float(argv[argv.index("--capex-fade") + 1]) if "--capex-fade" in argv else None   # growth mode: capex growth fades at this rate
    # default intensity mode: capex / revenue held at the current year's level in FY+1, eased by --capex-ease in FY+2 (0.85 = 15% lower intensity)
    cease = float(argv[argv.index("--capex-ease") + 1]) if "--capex-ease" in argv else 0.85
    # the most growth (either way) the street extrapolates a year; a guided quarter itself is taken as guided
    cap = float(argv[argv.index("--growth-cap") + 1]) if "--growth-cap" in argv else 0.5
    clamp = lambda x: max(-cap, min(cap, x))
    path = os.path.join(folder, "inputs.json")
    inp = json.load(open(path, encoding="utf-8"))
    ticker = inp["company"].get("filing_ticker") or inp["company"]["ticker"]   # SEC data ticker (GOOG -> GOOGL)
    F = kpis(ticker)
    K = F["kpis"]
    rev = K["revenue"]
    notes = []
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
    # ---- segments: the XBRL segment facts through atlas; a folder's segments.py only as a fallback, said out loud
    seg_defs = {}
    seg_mod = None
    seg_src = None
    if "--no-atlas-segments" not in argv:
        try:
            S = atlas_data.segments(ticker)
            if S["defs"]:
                seg_defs, seg_src = S["defs"], S["source"]
                for line, vals in S["lines"].items():
                    L[line] = {k: v for k, v in vals.items() if k // 10 >= since_fy - 1}
                notes.append(f"segments from {seg_src}: {list(seg_defs)} (members seen: {S['members_all']})")
        except atlas_data.NotCollected as exc:
            notes.append(f"atlas has no segment facts for {ticker} ({exc}); falling back")
    if not seg_defs and os.path.exists(os.path.join(folder, "segments.py")):
        spec = importlib.util.spec_from_file_location("ticker_segments", os.path.join(folder, "segments.py"))
        seg_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(seg_mod)
        seg_defs = getattr(seg_mod, "DEFINITIONS", {})
        seg_src = "press-release parse (segments.py, per-company fallback)"
        notes.append("WARNING: segments parsed by the folder's segments.py, not from atlas")
    # ---- guidance: sec.earnings_guidance through atlas; guidance.py's regexes only as a fallback
    releases = []
    gsrc = None
    if "--no-atlas-guidance" not in argv:
        try:
            releases = atlas_data.guidance_releases(ticker, since=f"{since_fy - 1}-01-01")
            if releases:
                gsrc = "sec.earnings_guidance via atlas"
        except atlas_data.NotCollected:
            releases = []
    if not releases:
        releases = guid.collect(ticker, folder, since=f"{since_fy - 1}-01-01")
        gsrc = "guidance.py regexes over the cached exhibits (fallback)"
        notes.append("WARNING: guidance from guidance.py regexes, not from atlas")
    if seg_mod:
        releases_px = guid.collect(ticker, folder, since=f"{since_fy - 1}-01-01") if gsrc.startswith("sec.") else releases
        q_ends = sorted((v["end"], k) for k, v in rev.items() if k % 10 != 0)
        for r in releases_px:
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
    # working capital: the TTM share of revenue reverts to the median share of the reported fiscal years by FY+2
    wc_years = sorted(k for k in L["wc_increase"] if k % 10 == 0 and (k // 10 < fy or q == 4) and L["revenue"].get(k))
    wc_med = statistics.median(L["wc_increase"][k] / L["revenue"][k] for k in wc_years) if wc_years else None
    wc_share = lambda y: wc_r if wc_med is None else wc_r + (wc_med - wc_r) * min(1.0, max(0.0, (y - fy) / 2))
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
    g_raw, g, g_capex = g, clamp(g), clamp(g_capex)
    if abs(g_raw - g) > 1e-12:
        notes.append(f"WARNING: street growth {g_raw:+.1%} capped at ±{cap:.0%} (--growth-cap)")
    # after a Q4 the reported year stays as filed: the street starts at FY+1 Q1, the quarter the latest release guides
    cur = fy + 1 if q == 4 else fy
    rq = [cur * 10 + i for i in range(q + 1 if q < 4 else 1, 5)]
    fy0, y1, y2 = cur * 10, (fy + 1) * 10, (fy + 2) * 10          # fy0: the year built from quarters (FY, or FY+1 after a Q4)
    fwd = [(y * 10, j) for j, y in enumerate(range(cur + 1, fy + 3), start=1)]   # the years after it, growth faded j times
    carry = {}
    for line in ("cash_and_st_investments", "debt", "investments", "minority_interest", "equity"):
        have = sorted(k for k in L.get(line, {}) if k <= latest)
        carry[line] = L[line][have[-1]] if have else 0.0      # some filers lack a recent value (e.g. no debt): carry the last one, else 0
    other = street_other_income(ticker, L, K, last4, ends, since, carry["cash_and_st_investments"], carry["debt"])
    if other["interest_income_ttm"] is None:
        notes.append(f"WARNING: forecast other income: {other['source']}")
    seg_g = {name: (ttm(f"seg:{name}", last4) / ttm(f"seg:{name}", prev4) - 1) if ttm(f"seg:{name}", prev4) else g for name in seg_defs}
    seg_m = {name: (ttm(f"segoi:{name}", last4) / ttm(f"seg:{name}", last4)) if ttm(f"seg:{name}", last4) else 0.0 for name in seg_defs}

    def put(k, revenue, capex, oi=None, other_income=None, wc=None):
        oi = revenue * margin if oi is None else oi
        oth = other["annual"] * (1 if k % 10 == 0 else 0.25) if other_income is None else other_income
        pre_k = oi + oth
        ni = pre_k * (1 - tax)
        vals = {"revenue": revenue, "operating_income": oi, "pretax_income": pre_k, "income_tax": pre_k * tax, "net_income": ni, "adjustments": 0.0,
                "adjusted_net_income": ni, "diluted_shares": shares, "dps": dps_q * (4 if k % 10 == 0 else 1), "dividends_total": dps_q * shares * (4 if k % 10 == 0 else 1),
                "d_and_a": revenue * da_r, "sbc": revenue * sbc_r, "wc_increase": revenue * wc_share(k // 10) if wc is None else wc, "capex": capex,
                "finance_lease_additions": capex * lease_r, "other_income": oth, "buybacks": 0.0}
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
                L[f"seg:{name}"][k] = p_ * (1 + clamp(seg_g[name] + (g_raw - g_ttm)))
                L.setdefault(f"segoi:{name}", {})[k] = L[f"seg:{name}"][k] * seg_m[name]
    qs = [cur * 10 + i for i in range(1, 5)]
    put(fy0, sum(L["revenue"][k] for k in qs), sum(L["capex"][k] for k in qs), sum(L["operating_income"][k] for k in qs),
        sum(L["other_income"].get(k, 0.0) for k in qs), sum(L["wc_increase"].get(k, 0.0) for k in qs))
    m_fwd = L["operating_income"][fy0] / L["revenue"][fy0]      # the built year's margin (actual quarters + guided quarter) carries forward
    inten = L["capex"][fy0] / L["revenue"][fy0]
    for yk, j in fwd:
        rev_y = L["revenue"][yk - 10] * (1 + g * fade ** j)
        cap_y = L["capex"][yk - 10] * (1 + g_capex * cfade ** j) if cfade is not None else rev_y * inten * (cease if yk == y2 else 1.0)
        put(yk, rev_y, cap_y, rev_y * m_fwd)
    for name in seg_defs:
        d = L.get(f"seg:{name}", {})
        if all(k in d for k in qs):
            d[fy0] = sum(d[k] for k in qs)
            L[f"segoi:{name}"][fy0] = sum(L[f"segoi:{name}"].get(k, 0.0) for k in qs)
            for yk, j in fwd:
                d[yk] = d[yk - 10] * (1 + clamp(seg_g[name]) * fade ** j)
                L[f"segoi:{name}"][yk] = d[yk] * seg_m[name]
    # balance items for the street: carry the latest actuals (bridge uses the latest reported quarter anyway)
    for line, v in carry.items():
        L.setdefault(line, {})
        for k in ([fy0] if q < 4 else []) + [y1, y2]:
            L[line][k] = v
    # ---- periods and metadata (after a Q4 the street is FY+1 and FY+2; FY+1's quarters stay lines, the engine values years)
    periods = [{"key": k, "year": k // 10, "q": k % 10, "status": "actual"} for k in sorted(set(L["revenue"]) & set(rev)) if k <= latest and k // 10 >= since_fy and (k % 10 != 0 or k // 10 < fy or q == 4)]
    periods += [{"key": k, "year": k // 10, "q": k % 10, "status": "consensus"} for k in (rq + [fy0] if q < 4 else []) + [y1, y2]]
    inp["periods"] = periods
    inp["lines"] = {line: {str(k): round(v, 6) for k, v in vals.items() if k // 10 >= since_fy - 1} for line, vals in L.items()}
    inp["segments"] = seg_defs
    inp["_sources"] = {"fundamentals": f"/research/fundamentals/{ticker}?currency=USD (company_type {F['company_type']}, per_share_divisor {F['per_share_divisor']}, native {F.get('native_unit')})",
                       "segments": seg_src, "guidance": gsrc, "notes": notes, "filled": dt.date.today().isoformat()}
    if F["per_share_divisor"] != 1.0:
        inp["market"]["_adr_note"] = f"per-share lines and share counts are per listed share (ADR), divisor {F['per_share_divisor']} applied by atlas_data.fundamentals"
    px = get(f"/api/v1/market/prices/{inp['company']['ticker']}", limit=1)["data"]["rows"][0]
    inp["market"].update({"price": float(px["close"]), "price_date": px["as_of_date"], "market_cap_musd_override": None})
    wc_txt = (f"{wc_r:.1%} of revenue (TTM) reverting to the {wc_med:.1%} median of FY{wc_years[0] // 10}-FY{wc_years[-1] // 10} by FY{fy + 2}"
              if wc_med is not None else f"{wc_r:.1%} of revenue (TTM; no reported fiscal year to revert to)")
    inp["as_of"].update({"latest_reported_fy": fy, "latest_reported_q": q, "balance_sheet_date": rev[latest]["end"],
                         "consensus_date": dt.date.today().isoformat(),
                         "consensus_source": (f"Guidance street built by fill_from_atlas.py on {dt.date.today()}: next-quarter revenue"
                                              + (" and operating income" if gd and gd.get("operating_income_next_quarter") else "")
                                              + f" from the {gd['date']} press release (beat-adjusted x{beat:.3f}" + (f", OI x{oi_beat:.3f}" if oi_beats else "") + ")" if gd else "momentum street")
                                             + (f"; FY{fy} is reported in full, the street starts at FY{fy + 1} Q1" if q == 4 else "")
                                             + f"; growth {g:+.1%}" + (f" (capped from {g_raw:+.1%} at ±{cap:.0%})" if abs(g_raw - g) > 1e-12 else "") + f" fading {fade:.0%}/yr"
                                             + f"; TTM margin {margin:.1%}, tax {tax:.1%}; capex {('growth %+.1f%% fading %.0f%%/yr' % (g_capex * 100, cfade * 100)) if cfade is not None else ('intensity held at %.1f%% of revenue in FY+1, x%.2f in FY+2' % (L['capex'][fy0] / L['revenue'][fy0] * 100, cease))}"
                                             + f"; working capital derived as NOPAT + D&A + SBC − OCF, {wc_txt}; other income {other['annual']:,.0f} a year: {other['source']}. Replace with sell-side consensus when available."})
    inp["_street"] = {"g": g, "g_uncapped": g_raw, "growth_cap": cap, "g_ttm": g_ttm, "g_capex": g_capex, "margin_ttm": margin, "tax_ttm": tax, "beat": beat, "oi_beat": oi_beat,
                      "da_ratio": da_r, "sbc_ratio": sbc_r, "wc_ratio": wc_r, "wc_ratio_median": wc_med, "wc_median_years": [k // 10 for k in wc_years],
                      "other_income": other, "street_start": rq[0] if rq else None,
                      "segment_growth": seg_g, "segment_margin": seg_m, "guidance_release": gd["date"] if gd else None}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(inp, fh, indent=1, ensure_ascii=False)
    print(json.dumps({"latest": latest, "price": inp["market"]["price"], "street": inp["_street"], "periods": len(periods), "segments": list(seg_defs), "sources": inp["_sources"]}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
