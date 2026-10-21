"""HTML valuation report for one ticker folder: the investment call and scenario matrix, the company-specific
argument (from the folder's narrative.py when present, else a generic method walkthrough) with live numbers, the full
three-scenario model and valuation tables, sensitivities, and the monitor block. Standard library only; Plotly via CDN.
"""
from __future__ import annotations

import copy
import datetime as dt
import html as H
import json

import importlib.util
import os

import valuation_engine as mm

SCN = ("bear", "base", "bull")
SCN_LABEL = {"bear": "Bear", "base": "Base", "bull": "Bull"}


# ----------------------------------------------------------------------------------------- formatting
def m(x, d=0):
    """USD millions with thousands separators; None -> em dash; negatives with a minus sign."""
    if x is None:
        return "—"
    return f"{x:,.{d}f}"


def pc(x, d=1, sign=False):
    if x is None:
        return "—"
    return f"{x * 100:{'+' if sign else ''}.{d}f}%"


def usd(x, d=0):
    if x is None:
        return "—"
    return f"-${-x:,.{d}f}" if x < 0 else f"${x:,.{d}f}"


def bn(x, d=1):
    """USD millions shown as $bn, or $tn above a trillion."""
    if x is None:
        return "—"
    if abs(x) >= 1_000_000:
        return f"${x / 1_000_000:,.2f}tn"
    return f"${x / 1000:,.{d}f}bn"


def esc(s) -> str:
    return H.escape(str(s))


def neg_class(x):
    return " neg" if isinstance(x, (int, float)) and x < 0 else ""


# ----------------------------------------------------------------------------------------- tables
ROW_SPECS = {
    "income": [
        ("Income statement", None, "head"),
        ("Total revenue", "revenue", "m"), ("  growth y/y", "yoy:revenue", "pct"),
        ("Family of Apps revenue", "seg:Family of Apps", "m"), ("  growth y/y", "yoy:seg:Family of Apps", "pct"),
        ("  Advertising", "seg:Advertising", "m"), ("    growth y/y", "yoy:seg:Advertising", "pct"),
        ("  Other revenue", "seg:Other Revenue", "m"), ("    growth y/y", "yoy:seg:Other Revenue", "pct"),
        ("Reality Labs revenue", "seg:Reality Labs", "m"), ("  growth y/y", "yoy:seg:Reality Labs", "pct"),
        ("Operating income", "operating_income", "m"), ("  growth y/y", "yoy:operating_income", "pct"), ("  operating margin", "margin", "pct"),
        ("Family of Apps operating income", "segoi:Family of Apps", "m"), ("  margin", "segm:Family of Apps", "pct"),
        ("Reality Labs operating income", "segoi:Reality Labs", "m"), ("  margin", "segm:Reality Labs", "pct"),
        ("Other income (expense)", "other_income", "m"),
        ("Pretax income", "pretax_income", "m"), ("  growth y/y", "yoy:pretax_income", "pct"),
        ("Income tax", "income_tax", "m"), ("  effective rate", "tax_rate", "pct"),
        ("Net income (GAAP)", "net_income", "m"), ("  growth y/y", "yoy:net_income", "pct"),
        ("Adjustments (non-GAAP)", "adjustments", "m"), ("Adjusted net income", "adjusted_net_income", "m"),
        ("Diluted weighted shares (m)", "diluted_shares", "m"),
        ("GAAP EPS", "eps", "ps"), ("  growth y/y", "yoy:eps", "pct"), ("Adjusted EPS", "adjusted_eps", "ps"),
        ("Dividends per share", "dps", "ps"), ("Dividends paid", "dividends_total", "m"), ("Share repurchases", "buybacks", "m"),
    ],
    "cash": [
        ("Cash flow", None, "head"),
        ("Depreciation & amortization", "d_and_a", "m"), ("  growth y/y", "yoy:d_and_a", "pct"),
        ("Stock-based compensation (expensed, not added back)", "sbc", "m"),
        ("Working-capital increase", "wc_increase", "m"),
        ("Operating cash flow (reported / consensus)", "operating_cash_flow", "m"),
        ("Capital expenditure", "capex", "m"), ("  growth y/y", "yoy:capex", "pct"),
        ("Finance-lease additions", "finance_lease_additions", "m"),
        ("NOPAT (operating income after tax)", "nopat", "m"),
        ("Unlevered free cash flow (FCFF)", "fcff", "m"),
    ],
    "balance": [
        ("Balance sheet (period end)", None, "head"),
        ("Cash and marketable securities", "cash_and_st_investments", "m"),
        ("Interest-bearing debt (incl. finance leases)", "debt", "m"),
        ("Net debt (cash)", "net_debt", "m"),
        ("Investments (equity-method + non-marketable)", "investments", "m"),
        ("Minority interest", "minority_interest", "m"),
        ("Shareholders' equity", "equity", "m"),
    ],
    "nongaap": [
        ("Non-GAAP and returns", None, "head"),
        ("EBITDA", "ebitda", "m"), ("  growth y/y", "yoy:ebitda", "pct"),
        ("ROIC (NOPAT / (equity + net debt), quarters annualised)", "roic", "pct"),
        ("Net reinvestment / revenue (transition path)", "reinvest_ratio", "pct"),
    ],
}


def model_table(model: mm.Model, scn: str, T: dict, cols: list[dict], section: str, which: str = "all") -> str:
    """One HTML table for a section of the model; `which` = 'all' | 'explicit' (through FY+2) | 'transition'."""
    if which == "explicit":
        cols = [c for c in cols if c["status"] != "extrapolated"]
    elif which == "transition":
        cols = [c for c in cols if c["status"] == "extrapolated" or c["key"] == model.fy2]
    head = "".join(f"<th class='{c['status']}{' annual' if c['annual'] else ''}'>{esc(c['label'])}</th>" for c in cols)
    body = []
    for label, row, kind in ROW_SPECS[section]:
        if kind == "head":
            body.append(f"<tr class='sect'><th colspan='{len(cols) + 1}'>{esc(label)}</th></tr>")
            continue
        vals = T.get(row, {})
        if not any(vals.get(c["key"]) is not None for c in cols):
            continue
        if which == "transition" and not any(vals.get(c["key"]) is not None for c in cols if c["status"] == "extrapolated"):
            continue
        indent = len(label) - len(label.lstrip(" "))
        cells = []
        for c in cols:
            v = vals.get(c["key"])
            txt = "—" if v is None else (pc(v) if kind == "pct" else (m(v, 2) if kind == "ps" else m(v)))
            cells.append(f"<td class='{c['status']}{' annual' if c['annual'] else ''}{neg_class(v)}'>{txt}</td>")
        body.append(f"<tr class='{'sub' if indent else ''}'><th style='padding-left:{10 + indent * 8}px'>{esc(label.strip())}</th>{''.join(cells)}</tr>")
    return f"<div class='tbl'><table><thead><tr><th>USD m</th>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"


def dcf_table(d: dict) -> str:
    rows = "".join(
        f"<tr><td>{'FY%d (H2 stub)' % (r['period'] // 10) if i == 0 else 'FY%d' % (r['period'] // 10)}</td><td>{'explicit' if r['stage'] == 1 else 'transition'}</td>"
        f"<td class='{neg_class(r['fcff'])}'>{m(r['fcff'])}</td><td>{r['t']:.2f}</td><td>{r['df']:.4f}</td><td class='{neg_class(r['pv'])}'>{m(r['pv'])}</td></tr>"
        for i, r in enumerate(d["rows"]))
    return (f"<div class='tbl'><table><thead><tr><th>Period</th><th>Stage</th><th>FCFF</th><th>Years from BS date</th><th>Discount factor</th><th>Present value</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></div>")


def bridge_table(sc: dict, w: dict, S: dict, price: float, label: str) -> str:
    d, mu = sc["dcf"], sc["multiples"]
    lines = [
        ("PV of explicit-period FCFF (through FY+2)", m(d["pv_stage1"])),
        ("PV of transition-period FCFF (FY+3 … FY+14)", m(d["pv_stage2"])),
        (f"Terminal value: NOPAT 2041 × (1 − g/ROIC) / (WACC − g), g {pc(S['terminal_growth'])}, ROIC {pc(S['steady_roic'], 0)}", m(d["terminal_value"])),
        (f"PV of terminal value (discounted {d['t_terminal']:.2f} years)", m(d["pv_terminal"])),
        ("<b>Enterprise value</b>", f"<b>{m(d['enterprise_value'])}</b>"),
        ("Less net debt (plus net cash)", m(-d["net_debt"])),
        ("Plus investments (equity-method + non-marketable)", m(d["investments"])),
        ("<b>Equity value</b>", f"<b>{m(d['equity_value'])}</b>"),
        ("Per diluted share, at the balance-sheet date", usd(d["value_per_share"], 2)),
        (f"× (1 + cost of equity {pc(w['cost_of_equity'], 2)}): value 12 months out", usd(d["value_per_share"] * (1 + w["cost_of_equity"]), 2)),
        ("Less next-12-month dividends per share", usd(-d["ntm_dps"], 2)),
        ("<b>DCF target</b>", f"<b>{usd(d['target'], 2)}</b>"),
        ("Terminal value as a share of EV", pc(d["terminal_share_of_ev"], 0)),
        ("Implied exit EV / EBITDA (2040)", f"{d['implied_exit_ev_ebitda']:.1f}x" if d["implied_exit_ev_ebitda"] else "—"),
    ]
    pe = [
        (f"Quarters 5-8 GAAP net income (w = {mu['weight_fy1']:.2f} on FY+1, {1 - mu['weight_fy1']:.2f} on FY+2)", m(mu["q5_q8_net_income"])),
        ("Quarters 5-8 diluted shares (m)", m(mu["q5_q8_shares"])),
        ("Quarters 5-8 EPS", usd(mu["q5_q8_eps"], 2)),
        ("Target P/E", f"{mu['target_multiple']:.1f}x"),
        ("<b>P/E target</b>", f"<b>{usd(mu['target'], 2)}</b>"),
        ("Implied P/E on FY+1 / FY+2 EPS", f"{mu['implied_pe_fy1']:.1f}x / {mu['implied_pe_fy2']:.1f}x"),
        (f"P/E the current price ({usd(price, 2)}) pays on quarters 5-8 EPS", f"{mu['price_implied_multiple']:.1f}x"),
    ]
    blend = [("DCF target × 50%", usd(d["target"] * 0.5, 2)), ("P/E target × 50%", usd(mu["target"] * 0.5, 2)),
             (f"<b>{label} blended target</b>", f"<b>{usd(sc['blended_target'], 2)}</b>"), ("vs price", pc(sc["upside"], 1, True))]

    def tbl(title, rows):
        return (f"<h4>{title}</h4><div class='tbl'><table><tbody>" +
                "".join(f"<tr><td>{a}</td><td class='num'>{b}</td></tr>" for a, b in rows) + "</tbody></table></div>")
    return tbl("DCF", lines) + tbl("P/E method", pe) + tbl("Blend", blend)


def wacc_table(w: dict, inputs: dict) -> str:
    W = inputs["wacc"]
    rows = [("Risk-free rate (10-year Treasury)", pc(W["risk_free"], 2)), ("Equity risk premium (NYU / Damodaran)", pc(W["erp"], 2)),
            ("Beta (Bloomberg-adjusted, 2-year weekly vs S&P 500)", f"{W['beta']:.3f}"),
            ("Cost of equity = rf + β × ERP", pc(w["cost_of_equity"], 2)),
            ("Market capitalisation (USD m)", m(w["market_cap"])), ("Interest-bearing debt (USD m)", m(w["debt"])),
            ("Equity weight / debt weight", f"{pc(w['weight_equity'], 1)} / {pc(w['weight_debt'], 1)}"),
            ("Pretax cost of debt", pc(W["pretax_cost_of_debt"], 2)), ("TTM effective tax rate", pc(w["ttm_tax_rate"], 1)),
            ("After-tax cost of debt", pc(w["after_tax_cost_of_debt"], 2)), ("<b>WACC</b>", f"<b>{pc(w['wacc'], 2)}</b>")]
    return "<div class='tbl'><table><tbody>" + "".join(f"<tr><td>{a}</td><td class='num'>{b}</td></tr>" for a, b in rows) + "</tbody></table></div>"


# ----------------------------------------------------------------------------------------- sensitivities
def sensitivities(inputs: dict) -> dict:
    base_in = copy.deepcopy(inputs)
    roics, margins = (0.20, 0.25, 0.30), (0.34, 0.36, 0.38)
    grid = []
    for r in roics:
        row = []
        for mg in margins:
            s = copy.deepcopy(base_in)
            s["scenarios"]["base"]["steady_roic"], s["scenarios"]["base"]["steady_margin"] = r, mg
            row.append(mm.Model(s).run()["scenarios"]["base"]["dcf"]["target"])
        grid.append(row)
    rfs = (0.040, 0.045, 0.050, 0.055)
    rf_row = []
    for rf in rfs:
        s = copy.deepcopy(base_in)
        s["wacc"]["risk_free"] = rf
        o = mm.Model(s).run()
        rf_row.append((rf, o["wacc"]["wacc"], o["scenarios"]["base"]["dcf"]["target"], o["scenarios"]["base"]["blended_target"]))
    out = mm.Model(base_in).run()
    eps = {k: out["scenarios"][k]["multiples"]["q5_q8_eps"] for k in SCN}
    targets = {k: inputs["scenarios"][k]["target_multiple"] for k in SCN}
    lo, hi = int(min(targets.values())) - 1, int(max(targets.values())) + 2
    mults = tuple(range(lo, hi + 1))
    pe_grid = [[eps[k] * x for x in mults] for k in SCN]
    return {"roics": roics, "margins": margins, "grid": grid, "rfs": rf_row, "eps": eps, "mults": mults, "pe_grid": pe_grid, "targets": targets}


def sens_html(sn: dict, out: dict) -> str:
    base = out["scenarios"]["base"]
    g = "<div class='tbl'><table><thead><tr><th>Base DCF target</th>" + "".join(f"<th>margin {pc(x, 0)}</th>" for x in sn["margins"]) + "</tr></thead><tbody>"
    for r, row in zip(sn["roics"], sn["grid"]):
        g += f"<tr><th>steady ROIC {pc(r, 0)}</th>" + "".join(
            f"<td class='num{' hl' if (abs(r - 0.25) < 1e-9 and abs(x - 0.36) < 1e-9) else ''}'>{usd(v)}</td>" for x, v in zip(sn["margins"], row)) + "</tr>"
    g += "</tbody></table></div>"
    p = "<div class='tbl'><table><thead><tr><th>P/E target = quarters 5-8 EPS × multiple</th>" + "".join(f"<th>{x}x</th>" for x in sn["mults"]) + "</tr></thead><tbody>"
    for k, row in zip(SCN, sn["pe_grid"]):
        tgt = sn["targets"][k]
        p += f"<tr><th>{SCN_LABEL[k]} EPS {usd(sn['eps'][k], 2)}</th>" + "".join(f"<td class='num{' hl' if abs(x - tgt) < 1e-9 else ''}'>{usd(v)}</td>" for x, v in zip(sn["mults"], row)) + "</tr>"
    p += "</tbody></table></div>"
    r = "<div class='tbl'><table><thead><tr><th>Risk-free rate</th><th>WACC</th><th>Base DCF</th><th>Base blended</th></tr></thead><tbody>"
    for rf, w, d, b in sn["rfs"]:
        r += f"<tr><th>{pc(rf, 2)}</th><td class='num'>{pc(w, 2)}</td><td class='num'>{usd(d)}</td><td class='num'>{usd(b)}</td></tr>"
    r += "</tbody></table></div>"
    return (f"<p>Base DCF ({usd(base['dcf']['target'])}) against the two most subjective steady-state assumptions. The highlighted cell is the house base case.</p>{g}"
            f"<p>The P/E leg is linear in the multiple: every turn of P/E is worth about {usd(sn['eps']['base'])} per share on base-case EPS.</p>{p}"
            f"<p>Discount rate: the risk-free rate the monitor uses is the live 10-year yield.</p>{r}")


# ----------------------------------------------------------------------------------------- charts data
def chart_payload(model: mm.Model, out: dict, tables: dict, inputs: dict) -> str:
    cols = model.period_meta()
    years = [c for c in cols if c["annual"] and c["key"] >= model.fy * 10]
    fc = {k: [tables[k]["fcff"].get(c["key"]) for c in years] for k in SCN}
    # the current-year column is the full fiscal year; the DCF uses the H2 stub (shown in the DCF table)
    labels = [c["label"].replace("E", "") for c in years]
    rev = [tables["base"]["revenue"].get(c["key"]) for c in years]
    mg = [tables["base"]["margin"].get(c["key"]) for c in years]
    capex = [tables["base"]["capex"].get(c["key"]) for c in years]
    hist_years = [c for c in cols if c["annual"] and c["status"] == "actual"]
    hist_labels = [c["label"] for c in hist_years]
    hist_rev = [tables["base"]["revenue"].get(c["key"]) for c in hist_years]
    hist_mg = [tables["base"]["margin"].get(c["key"]) for c in hist_years]
    hist_capex = [tables["base"]["capex"].get(c["key"]) for c in hist_years]
    s, h = out["scenarios"], out["house"]
    R = inputs["reference_multiples"]
    return json.dumps({
        "price": out["price"],
        "tgt": {"names": ["Bear", "Base", "Bull", "House"],
                "dcf": [s["bear"]["dcf"]["target"], s["base"]["dcf"]["target"], s["bull"]["dcf"]["target"], h["dcf_target"]],
                "pe": [s["bear"]["multiples"]["target"], s["base"]["multiples"]["target"], s["bull"]["multiples"]["target"], h["multiples_target"]],
                "blend": [s["bear"]["blended_target"], s["base"]["blended_target"], s["bull"]["blended_target"], h["target"]], "tpl_label": inputs.get("baseline", {}).get("label", "Baseline")},
        "fc": {"labels": labels, "bear": fc["bear"], "base": fc["base"], "bull": fc["bull"],
               "stage": ["explicit" if c["status"] == "forecast" else "transition" for c in years]},
        "rev": {"labels": hist_labels + labels, "rev": hist_rev + rev, "margin": hist_mg + mg, "capex": hist_capex + capex,
                "n_hist": len(hist_years)},
        "pe": {"low": round(R["pe5y_low"], 1), "avg": round(R["pe5y_avg"], 1), "high": round(R["pe5y_high"], 1), "now": s["base"]["multiples"]["price_implied_multiple"],
               "bear": inputs["scenarios"]["bear"]["target_multiple"], "base": inputs["scenarios"]["base"]["target_multiple"], "bull": inputs["scenarios"]["bull"]["target_multiple"]},
    })


# ----------------------------------------------------------------------------------------- the page
def render(inputs: dict, out: dict, live: dict, new_q: list[int], avc: dict, applied_notes: list[str], rules_eval: list[dict], folder: str = None) -> str:
    model = mm.Model(inputs)
    a, s, h, w = inputs["as_of"], out["scenarios"], out["house"], out["wacc"]
    S = inputs["scenarios"]
    price = out["price"]
    base_tpl = inputs.get("baseline", {})
    bl_label = base_tpl.get("label", "Baseline")
    co, tk = inputs["company"]["name"], inputs["company"]["ticker"]
    tm = S["base"]["target_multiple"]
    today = dt.date.today().isoformat()
    price_date = live.get("price", {}).get("date", inputs["market"].get("price_date"))
    cols = model.period_meta()
    tables = {k: model.table(k) for k in SCN}
    sn = sensitivities(inputs)
    fired = [r for r in rules_eval if r["fired"]]
    e = live.get("earnings") or {}
    b = live.get("beta") or {}
    R = inputs["reference_multiples"]
    bs, bm = s["base"], s["base"]["multiples"]
    fy, q = a["latest_reported_fy"], a["latest_reported_q"]
    T = tables["base"]
    y1, y2 = model.fy1, model.fy2
    errs = {k: v["error"] for k, v in live.items() if isinstance(v, dict) and "error" in v}

    # ---- verdict text
    if price <= s["bear"]["blended_target"]:
        where = f"below the bear-case value ({usd(s['bear']['blended_target'])}): the market is paying for less than consensus with no premium"
    elif price <= s["base"]["blended_target"]:
        where = (f"between the bear case ({usd(s['bear']['blended_target'])}) and the base case ({usd(s['base']['blended_target'])}): "
                 f"you are paid {pc(s['base']['upside'], 0, True)} if the house adjustments play out, and lose {pc(s['bear']['upside'], 0, True)} if {esc(co)} merely meets consensus")
    elif price <= s["bull"]["blended_target"]:
        where = f"between the base case ({usd(s['base']['blended_target'])}) and the bull case ({usd(s['bull']['blended_target'])}): the house view is largely priced in"
    else:
        where = f"above the bull case ({usd(s['bull']['blended_target'])}): the price needs more than the most optimistic scenario"
    verdict = (f"At {usd(price, 2)} the stock trades {where}. The price pays {bm['price_implied_multiple']:.1f}x the model's quarters-5-8 EPS "
               f"({usd(bm['q5_q8_eps'], 2)}), against {esc(co)}'s own five-year forward range of {R['pe5y_low']:.1f}x-{R['pe5y_high']:.1f}x (average {R['pe5y_avg']:.1f}x) and the {tm:.0f}x the base case assigns. "
               f"House 12-month target {usd(h['target'])} ({pc(h['upside'], 1, True)}); rule in force: <b>{esc(fired[0]['name']) if fired else 'none'}</b>.")

    # ---- scenario matrix
    def adj(line, key, scn):
        return model.pp(line, key, scn)
    q3, q4 = (model.fc_quarters[0], model.fc_quarters[-1]) if model.fc_quarters else (None, None)
    adj_lines = []
    for r in inputs["adjustments"]:
        if r["line"] not in adj_lines:
            adj_lines.append(r["line"])
    nice = lambda line: "Capex" if line in mm.CAPEX_LINE_ALIASES else ("Total revenue" if line in mm.REVENUE_LINE_ALIASES else ("Operating margin" if line in mm.MARGIN_LINE_ALIASES else line))
    matrix_rows = [("<b>What you must believe</b>", "", "", "", "")]
    for line in adj_lines:
        unit = "pp" if line in mm.MARGIN_LINE_ALIASES else "growth"
        if model.fc_quarters:
            matrix_rows.append((f"{nice(line)} {unit} vs consensus, next quarter(s)",
                                *[pc(sum(adj(line, k, x) for k in model.fc_quarters) / len(model.fc_quarters), 0, True) for x in SCN], ""))
        matrix_rows.append((f"{nice(line)} {unit} vs consensus, FY{y1 // 10} / FY{y2 // 10}",
                            *[f"{pc(adj(line, y1, x), 0, True)} / {pc(adj(line, y2, x), 0, True)}" for x in SCN], ""))
    matrix_rows += [
        ("Steady-state ROIC (terminal)", *[pc(S[x]["steady_roic"], 0) for x in SCN], ""),
        ("Steady-state operating margin", *[pc(S[x]["steady_margin"], 0) for x in SCN], ""),
        ("Terminal growth", *[pc(S[x]["terminal_growth"], 1) for x in SCN], ""),
        ("Target P/E on quarters 5-8 EPS", *[f"{S[x]['target_multiple']:.0f}x" for x in SCN], f"{h['implied_multiple']:.1f}x implied"),
        ("<b>What you get</b>", "", "", "", ""),
        (f"Revenue CAGR FY{fy - 1}-FY{fy + 4}", *[pc(s[x]["revenue_cagr_5y"], 1) for x in SCN], ""),
        ("Quarters 5-8 EPS", *[usd(s[x]["multiples"]["q5_q8_eps"], 2) for x in SCN], ""),
        ("DCF target", *[usd(s[x]["dcf"]["target"]) for x in SCN], usd(h["dcf_target"])),
        ("P/E target", *[usd(s[x]["multiples"]["target"]) for x in SCN], usd(h["multiples_target"])),
        ("<b>Blended 12-month target</b>", *[f"<b>{usd(s[x]['blended_target'])}</b>" for x in SCN], f"<b>{usd(h['target'])}</b>"),
        ("vs price", *[pc(s[x]["upside"], 1, True) for x in SCN], pc(h["upside"], 1, True)),
    ]
    if base_tpl.get("base") is not None:
        matrix_rows.append((f"{esc(bl_label)}", *[usd(base_tpl.get(x)) for x in SCN], usd(base_tpl.get("house"))))
    matrix = "<div class='tbl'><table><thead><tr><th></th><th>Bear</th><th>Base</th><th>Bull</th><th>House</th></tr></thead><tbody>"
    for r in matrix_rows:
        cls = " class='sect'" if r[0].startswith("<b>What") else ""
        matrix += f"<tr{cls}><th>{r[0]}</th>" + "".join(f"<td class='num'>{c}</td>" for c in r[1:]) + "</tr>"
    matrix += "</tbody></table></div>"

    # ---- narrative numbers (base)
    nopat27, da27, capex27, wc27, fcff27 = (T["nopat"][y1], T["d_and_a"][y1], T["capex"][y1], T["wc_increase"][y1], T["fcff"][y1])
    stub = bs["dcf"]["rows"][0]["fcff"]
    first_pos = next((c["label"] for c in cols if c["annual"] and T["fcff"].get(c["key"], -1) > 0 and c["key"] > fy * 10), "—")
    cons_eps = inputs["lines"]["net_income"].get(str(y1), 0) * bm["weight_fy1"] + inputs["lines"]["net_income"].get(str(y2), 0) * (1 - bm["weight_fy1"])
    cons_eps = cons_eps / bm["q5_q8_shares"] if bm["q5_q8_shares"] else None
    ad_q3 = T["seg:Advertising"].get(q3) if q3 else None
    ad_q3_cons = inputs["lines"]["seg:Advertising"].get(str(q3)) if q3 else None
    roic_hist = [(c["label"], T["roic"].get(c["key"])) for c in cols if c["status"] == "actual" and c["annual"] and T["roic"].get(c["key"])]

    def article(title, body):
        return f"<article class='talk'><h3>{title}</h3>{body}</article>"

    ctx = {"inputs": inputs, "out": out, "model": model, "tables": tables, "cols": cols, "label_of": {c["key"]: c["label"] for c in cols},
           "live": live, "s": s, "h": h, "w": w, "S": S, "price": price, "a": a, "fy": fy, "q": q, "y1": y1, "y2": y2, "q3": q3, "q4": q4,
           "T": T, "bs": bs, "bm": bm, "R": R, "b": b, "verdict": verdict, "baseline": base_tpl,
           "nopat1": nopat27, "da1": da27, "capex1": capex27, "wc1": wc27, "fcff1": fcff27, "stub": stub, "first_pos": first_pos,
           "cons_eps": cons_eps, "roic_hist": roic_hist, "wacc_table": wacc_table(w, inputs),
           "usd": usd, "pc": pc, "m": m, "bn": bn, "esc": esc, "article": article}
    narrative, narrative_title, narrative_sub = None, "The argument", ""
    if folder and os.path.exists(os.path.join(folder, "narrative.py")):
        spec = importlib.util.spec_from_file_location("ticker_narrative", os.path.join(folder, "narrative.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        narrative = "".join(article(t, body) for t, body in mod.sections(ctx))
        narrative_title = getattr(mod, "TITLE", narrative_title)
        narrative_sub = getattr(mod, "SUBTITLE", "")
    if narrative is None:
        narrative_sub = "A generic walkthrough of the method with this ticker's numbers; add narrative.py to the ticker folder for the company-specific argument."
        narrative = "".join([
            article("1. How the DCF works", f"""<p>A company is worth the cash it will generate, discounted because future dollars are worth less than today's. The cash in question is <b>unlevered free cash flow</b>: operating profit after tax, plus depreciation, minus the reinvestment needed to keep growing (capex, leases, working capital).</p>
<p>FY{y1 // 10} in the base case: NOPAT {bn(nopat27)} + D&A {bn(da27)} − capex {bn(capex27)} + working capital and other {bn(-wc27)} = <b>FCFF {bn(fcff27)}</b>. Consensus is the starting point; the house adjustments are layered on top (see the assumptions section).</p>"""),
            article("2. Three periods", f"""<div class='timeline'><div><span>FY{fy} H2 – FY{y2 // 10}</span><b>Explicit period</b><small>Consensus plus house uplifts.</small></div>
<div><span>FY{y2 // 10 + 1} – FY{model.years_ext[-1][0] // 10}</span><b>Transition ({model.n_conv} years)</b><small>Every driver glides linearly to the steady state.</small></div>
<div><span>After FY{model.years_ext[-1][0] // 10}</span><b>Perpetual</b><small>Terminal growth {pc(S['base']['terminal_growth'])}, steady ROIC {pc(S['base']['steady_roic'], 0)}.</small></div></div>
<p>Historical ROIC in this model's measure: {', '.join(f'{l} {pc(v, 0)}' for l, v in roic_hist) or 'n/a'}. FCFF turns positive in <b>{first_pos}</b>.</p><div id='c_fc' class='chart tall'></div>"""),
            article("3. Discount rate and the bridge to a target", f"""<p>WACC <b>{pc(w['wacc'], 2)}</b>: risk-free {pc(inputs['wacc']['risk_free'], 2)}, ERP {pc(inputs['wacc']['erp'])}, beta {inputs['wacc']['beta']:.2f}.</p>{wacc_table(w, inputs)}
<p>Enterprise value {bn(bs['dcf']['enterprise_value'])}, equity {bn(bs['dcf']['equity_value'])}, {usd(bs['dcf']['value_per_share'])} per share at {a['balance_sheet_date']}; rolled a year forward at the cost of equity less dividends: <b>base DCF target {usd(bs['dcf']['target'])}</b>.</p>"""),
            article("4. The multiple and the blend", f"""<p>Quarters 5-8 GAAP EPS {usd(bm['q5_q8_eps'], 2)} (consensus about {usd(cons_eps, 2)}) × {tm:.0f}x = <b>{usd(bm['target'])}</b>; own five-year forward range {R['pe5y_low']:.1f}x / {R['pe5y_avg']:.1f}x / {R['pe5y_high']:.1f}x, price today {bm['price_implied_multiple']:.1f}x.</p><div id='c_pe' class='chart short'></div>
<p>50% DCF + 50% P/E: bear <b>{usd(s['bear']['blended_target'])}</b>, base <b>{usd(bs['blended_target'])}</b>, bull <b>{usd(s['bull']['blended_target'])}</b>; house target {usd(h['target'])} ({pc(h['upside'], 0, True)}).</p><div id='c_tgt' class='chart'></div>"""),
        ])

    # ---- model and valuation sections with scenario toggles
    def scen_blocks(fn):
        return "".join(f"<div class='scn' data-scn='{k}'{' hidden' if k != 'base' else ''}>{fn(k)}</div>" for k in SCN)

    def model_section(k):
        T_ = tables[k]
        return (f"<h4>Explicit period: actuals, consensus and house adjustments (FY{fy - 2} – FY{y2 // 10})</h4>"
                + "".join(model_table(model, k, T_, cols, sec, "explicit") for sec in ("income", "cash", "balance", "nongaap"))
                + f"<h4>Transition period FY{y2 // 10 + 1} – FY{model.years_ext[-1][0] // 10}: convergence to the {SCN_LABEL[k].lower()} steady state</h4>"
                + model_table(model, k, T_, cols, "income", "transition")
                + model_table(model, k, T_, cols, "cash", "transition")
                + model_table(model, k, T_, cols, "nongaap", "transition"))

    def valuation_section(k):
        sc = s[k]
        return f"<h4>Discounted cash flows ({SCN_LABEL[k]})</h4>{dcf_table(sc['dcf'])}{bridge_table(sc, w, S[k], price, SCN_LABEL[k])}"

    toggle = "<div class='toggle' role='tablist'>" + "".join(
        f"<button role='tab' data-scn='{k}' class='{'on' if k == 'base' else ''}'>{SCN_LABEL[k]}</button>" for k in SCN) + "</div>"

    # ---- adjustments sheet
    label_of = {c["key"]: c["label"] for c in cols}
    adj_rows = "".join(f"<tr><td>{esc(r['line']).replace('资本开支', 'Capex')}</td><td>{esc(label_of.get(int(r['period_key']), r['period_key']))}</td>"
                       f"<td class='num'>{pc(r['bear'], 0, True)}</td><td class='num'>{pc(r['base'], 0, True)}</td><td class='num'>{pc(r['bull'], 0, True)}</td></tr>"
                       for r in inputs["adjustments"])
    settings = [("Ticker / company", f"{inputs['company']['ticker']} / {inputs['company']['name']}"), ("Fiscal year end", f"month {inputs['company']['fiscal_year_end_month']}"),
                ("Latest reported quarter / balance-sheet date", f"FY{fy} Q{q} / {a['balance_sheet_date']}"),
                ("Consensus block", f"{a['consensus_date']} — {esc(a['consensus_source'])}"),
                ("Price used", f"{usd(price, 2)} ({price_date})"), ("DCF weight / multiple type / earnings basis", f"{pc(inputs['blend']['dcf_weight'], 0)} / {inputs['blend']['multiple_type']} / {inputs['blend']['earnings_basis']}"),
                ("House position between base and bull", pc(inputs["blend"]["target_position"], 0, True)), ("Rating", esc(inputs["rating"]["label"]))]
    settings_html = "<div class='tbl'><table><tbody>" + "".join(f"<tr><td>{k_}</td><td>{v}</td></tr>" for k_, v in settings) + "</tbody></table></div>"

    # ---- monitor block
    rules_html = "".join(f"<li class='{'fired' if r['fired'] else ''}'><b>{esc(r['name'])}</b> — {esc(r['action'])} <code>{esc(r['when'])}</code></li>" for r in rules_eval)
    def fmt_val(v):
        if isinstance(v, list):
            return ", ".join(f"{x:.3f}" if isinstance(x, float) else str(x) for x in v)
        return f"{v:.4f}" if isinstance(v, float) else str(v)
    checks_html = "".join(
        "<li class='%s'>%s %s: %s</li>" % ("ok" if c["ok"] else ("warn" if c.get("warn_only") else "fail"),
                                           "✓" if c["ok"] else ("！" if c.get("warn_only") else "✗"), esc(c["check"]), esc(fmt_val(c["value"])))
        for c in out["checks"])
    live_items = "".join(f"<li>{x}</li>" for x in [
        f"Risk-free (10y UST, {live.get('dgs10', {}).get('date', 'manual')}): {pc(inputs['wacc']['risk_free'], 2)}",
        f"Beta {inputs['wacc']['beta']:.3f}" + (f" — raw 2y weekly vs SPY {b['raw']:.3f}, n={b['n_weeks']} ({b['from']}..{b['to']})" if b else " (manual)") + (f"; {esc(bl_label)} {base_tpl['beta']:.3f}" if base_tpl.get('beta') is not None else ''),
        f"WACC {pc(w['wacc'], 2)}" + (f" ({esc(bl_label)} {pc(base_tpl['wacc'], 2)})" if base_tpl.get('wacc') is not None else '') + f"; cost of equity {pc(w['cost_of_equity'], 2)}; E/V {pc(w['weight_equity'], 1)}",
        f"Price-implied P/E on quarters 5-8 EPS: {bm['price_implied_multiple']:.1f}x vs {tm:.0f}x target"])
    newq_html = f"<p>None yet: SEC XBRL shows FY{fy} Q{q} as the latest 10-Q/10-K.</p>" if not new_q else ""
    for key in new_q:
        t = "".join(f"<tr><td>{esc(r['kpi'])}</td><td class='num'>{m(r['actual'], 2 if r['kpi'] in ('dividends_per_share', 'eps_diluted') else 0)}</td>"
                    f"<td class='num'>{m(r['consensus'], 2 if r['kpi'] in ('dividends_per_share', 'eps_diluted') else 0)}</td><td class='num'>{pc(r['surprise'], 1, True)}</td></tr>" for r in avc.get(key, []))
        newq_html += (f"<p><b>FY{key // 10} Q{key % 10} is filed.</b> Actual vs the consensus the model carried (USD m; per-share items per share; shares m):</p>"
                      f"<div class='tbl'><table><thead><tr><th>KPI</th><th>Actual</th><th>Consensus</th><th>Surprise</th></tr></thead><tbody>{t}</tbody></table></div>"
                      "<p>To roll the model: run the monitor with <code>--apply-actuals</code>, then key in the segment lines from the press release and refresh the consensus block.</p>")
    if applied_notes:
        newq_html += "<p>Applied to inputs.json:</p><ul>" + "".join(f"<li>{esc(n)}</li>" for n in applied_notes) + "</ul>"
    err_html = ("<p class='fail'>Live fetch failed for: " + ", ".join(f"{k} ({esc(str(v)[:80])})" for k, v in errs.items()) + ". Those inputs are carried from inputs.json.</p>") if errs else ""
    watch_items = []
    for line in adj_lines:
        if line in mm.CAPEX_LINE_ALIASES:
            watch_items.append(f"<li><b>Capex and capex guidance.</b> Base case carries {bn(T['capex'][y1], 0)} for FY{y1 // 10} ({pc(adj(line, y1, 'base'), 0, True)} over consensus), bull {pc(adj(line, y1, 'bull'), 0, True)}.</li>")
        elif q3 and f"seg:{line}" in T:
            mv, cv = T[f"seg:{line}"].get(q3), inputs["lines"].get(f"seg:{line}", {}).get(str(q3))
            watch_items.append(f"<li><b>{esc(line)} growth vs consensus.</b> The thesis is {pc(adj(line, q3, 'base'), 0, True)} (base) to {pc(adj(line, q3, 'bull'), 0, True)} (bull). Model carries {m(mv)} vs consensus {m(cv)} for {label_of.get(q3, '')} ({pc(mv / cv - 1, 1, True) if mv and cv else '—'}).</li>")
    if q3:
        segs_m = ", ".join(f"{esc(sg)} {pc(T.get(f'segm:{sg}', {}).get(q3))}" for sg in inputs["segments"] if T.get(f"segm:{sg}", {}).get(q3) is not None)
        watch_items.append(f"<li><b>Operating margin.</b> Model: {pc(T['margin'].get(q3))} for {label_of.get(q3, '')}" + (f", {pc(T['margin'].get(q4))} for {label_of.get(q4, '')}" if q4 and q4 != q3 else "") + (f"; segments {segs_m}" if segs_m else "") + ".</li>")
    watch_items.append("<li><b>After the print:</b> run the monitor with <code>--apply-actuals</code>, key in the segment split, refresh the consensus block, rerun.</li>")
    watch = "<ul>" + "".join(watch_items) + "</ul>"

    payload = chart_payload(model, out, tables, inputs)
    nav = [("call", "The call"), ("argument", "The argument"), ("model", "Financial model"), ("valuation", "Valuation"),
           ("sens", "Sensitivities"), ("inputs", "Assumptions"), ("monitor", "Monitor"), ("sources", "Sources")]
    nav_html = "".join(f"<a href='#{i}'>{t}</a>" for i, t in nav)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(tk)} valuation report {today}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{{color-scheme:light dark;--surface:#fcfcfb;--surface-2:#f1f0ec;--surface-3:#e8e6e0;--text:#0b0b0b;--text-2:#52514e;--muted:#8a8882;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--good:#008300;--warn:#b87a00;--bad:#c73c3b;--line:#dcdad4;--act:transparent;--fc:#eaf2fc;--ext:#e9f6f0;--hl:#fff3cc}}
@media (prefers-color-scheme:dark){{:root{{--surface:#1a1a19;--surface-2:#242422;--surface-3:#2e2d2a;--text:#f0efec;--text-2:#c3c2b7;--muted:#8d8c85;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--warn:#c98500;--bad:#e66767;--line:#3a3936;--fc:#1f2a3a;--ext:#1e2f27;--hl:#3b3416}}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--surface);color:var(--text);font:15px/1.55 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif}}
nav{{position:sticky;top:0;z-index:5;background:var(--surface);border-bottom:1px solid var(--line);padding:8px 16px;display:flex;gap:4px;overflow-x:auto;white-space:nowrap}}
nav a{{color:var(--text-2);text-decoration:none;padding:6px 10px;border-radius:999px;font-size:13px}} nav a:hover{{background:var(--surface-2);color:var(--text)}}
main{{max-width:1180px;margin:0 auto;padding:24px 16px 64px}}
h1{{font-size:26px;margin:0 0 6px;letter-spacing:-.01em}} h2{{font-size:20px;margin:48px 0 12px;padding-top:8px;border-top:2px solid var(--line)}} h3{{font-size:16px;margin:22px 0 6px}} h4{{font-size:14px;margin:22px 0 6px;color:var(--text-2);text-transform:uppercase;letter-spacing:.04em}}
p{{margin:8px 0}} .sub{{color:var(--text-2)}} small{{color:var(--muted)}}
.hero{{display:grid;grid-template-columns:1.3fr 1fr;gap:20px;margin:18px 0;align-items:start}} @media(max-width:860px){{.hero{{grid-template-columns:1fr}}}}
.verdict{{background:var(--surface-2);border-left:4px solid var(--s1);border-radius:10px;padding:14px 18px;font-size:16px}}
.tiles{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}} .tile{{background:var(--surface-2);border-radius:10px;padding:12px 14px}} .tile .k{{font-size:12px;color:var(--text-2)}} .tile .v{{font-size:26px;font-weight:650;letter-spacing:-.01em}} .tile .n{{font-size:12px;color:var(--muted)}}
.tbl{{overflow-x:auto;margin:8px 0 16px;border:1px solid var(--line);border-radius:8px}} table{{border-collapse:separate;border-spacing:0;width:100%;font-size:13px;font-variant-numeric:tabular-nums}}
th,td{{padding:5px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}} th:first-child,td:first-child{{text-align:left}}
thead th{{position:sticky;top:0;background:var(--surface-2);color:var(--text-2);font-weight:600;font-size:12px;z-index:2}} thead th:first-child{{left:0;z-index:3}} td:first-child{{white-space:normal;min-width:160px}}
tbody th{{position:sticky;left:0;background:var(--surface);font-weight:500;text-align:left;z-index:1;min-width:230px;max-width:340px;white-space:normal}}
tr.sect th{{background:var(--surface-2);color:var(--text);font-weight:650;text-align:left;padding-top:10px}} tr.sub th{{color:var(--text-2);font-size:12px}} tr.sub td{{color:var(--text-2);font-size:12px}}
td.forecast,th.forecast{{background:var(--fc)}} td.extrapolated,th.extrapolated{{background:var(--ext)}} td.annual,th.annual{{font-weight:600}} td.neg{{color:var(--bad)}} td.num{{text-align:right}} td.hl{{background:var(--hl);font-weight:650}}
.legend{{display:flex;gap:14px;font-size:12px;color:var(--text-2);margin:4px 0 10px}} .legend i{{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-2px;margin-right:4px;border:1px solid var(--line)}}
.toggle{{display:inline-flex;background:var(--surface-2);border-radius:999px;padding:3px;margin:6px 0 10px}} .toggle button{{border:0;background:transparent;color:var(--text-2);padding:6px 16px;border-radius:999px;font:inherit;font-size:13px;cursor:pointer}} .toggle button.on{{background:var(--s1);color:#fff}}
.talk{{background:var(--surface-2);border-radius:10px;padding:14px 18px;margin:12px 0}} .talk h3{{margin-top:0}}
.timeline{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:10px 0}} .timeline div{{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px}} .timeline span{{display:block;font-size:12px;color:var(--muted)}} .timeline b{{display:block;margin:2px 0}} .timeline small{{display:block;color:var(--text-2)}}
.chart{{height:340px;margin:8px 0}} .chart.tall{{height:380px}} .chart.short{{height:220px}} .charts2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}} @media(max-width:860px){{.charts2{{grid-template-columns:1fr}}}}
ul{{padding-left:20px}} li{{margin:4px 0}} li.fired{{background:color-mix(in srgb,var(--bad) 12%,transparent);border-radius:6px;padding:4px 8px;margin-left:-8px}} li.warn{{color:var(--warn)}} li.fail,p.fail{{color:var(--bad)}} code{{font-size:12px;color:var(--muted)}}
details{{margin:8px 0}} summary{{cursor:pointer;color:var(--text-2)}} footer{{margin-top:40px;color:var(--muted);font-size:12px}}
@media print{{nav{{display:none}} .scn[hidden]{{display:block!important}} .toggle{{display:none}} .chart{{break-inside:avoid}} body{{font-size:11px}}}}
</style></head><body>
<nav>{nav_html}</nav>
<main>
<h1 id="call">{esc(co)} ({esc(tk)}) — valuation and the investment call</h1>
<p class="sub">Report date {today} · price {usd(price, 2)} ({price_date}) · latest reported quarter FY{fy} Q{q} (balance sheet {a['balance_sheet_date']}) · consensus block {a['consensus_date']}
{('· next earnings <b>' + esc(e.get('report_date')) + '</b> (' + esc(e.get('time_of_day')) + ', ' + esc(e.get('fiscal_quarter')) + '), Nasdaq EPS consensus ' + esc(e.get('eps_consensus_nasdaq'))) if e.get('report_date') else ''}</p>
{err_html}
<div class="hero">
<div><div class="verdict">{verdict}</div>
<h3>What to watch at the next print</h3>{watch}</div>
<div class="tiles">
<div class="tile"><div class="k">House 12-month target</div><div class="v">{usd(h['target'])}</div><div class="n">{(esc(bl_label) + " " + usd(base_tpl.get("house"))) if base_tpl.get("house") else "50% DCF + 50% P/E, house position " + pc(h["position"], 0, True)}</div></div>
<div class="tile"><div class="k">Upside to house target</div><div class="v">{pc(h['upside'], 1, True)}</div><div class="n">{esc(fired[0]['name']) if fired else 'no rule fired'}</div></div>
<div class="tile"><div class="k">Bear · Base · Bull</div><div class="v">{s['bear']['blended_target']:,.0f} · {s['base']['blended_target']:,.0f} · {s['bull']['blended_target']:,.0f}</div><div class="n">50% DCF + 50% P/E</div></div>
<div class="tile"><div class="k">Price-implied forward P/E</div><div class="v">{bm['price_implied_multiple']:.1f}x</div><div class="n">target {tm:.0f}x · 5y range {R['pe5y_low']:.1f}–{R['pe5y_high']:.1f}x</div></div>
<div class="tile"><div class="k">WACC</div><div class="v">{pc(w['wacc'], 2)}</div><div class="n">rf {pc(inputs['wacc']['risk_free'], 2)} · β {inputs['wacc']['beta']:.2f} · ERP {pc(inputs['wacc']['erp'])}</div></div>
<div class="tile"><div class="k">Base revenue CAGR FY{fy - 1}–FY{fy + 4}</div><div class="v">{pc(bs['revenue_cagr_5y'], 1)}</div><div class="n">quarters 5-8 op. margin {pc(bs['q5_q8_operating_margin'], 1)}</div></div>
</div></div>
<h3>Scenario matrix: what you must believe, and what you get</h3>{matrix}
<div class="charts2"><div id="c_tgt_top" class="chart"></div><div id="c_rev" class="chart"></div></div>

<h2 id="argument">{esc(narrative_title)}</h2>
<p class="sub">{narrative_sub}</p>
{narrative}

<h2 id="model">Financial model</h2>
<p class="sub">Every row of the forecast sheet. Columns: <span class="legend"><span><i style="background:var(--act)"></i>actual (SEC XBRL)</span><span><i style="background:var(--fc)"></i>consensus + house adjustments</span><span><i style="background:var(--ext)"></i>transition years (model)</span></span> Annual columns in bold. Switch scenarios with the toggle; the toggle also drives the valuation section.</p>
{toggle}
{scen_blocks(model_section)}

<h2 id="valuation">Valuation</h2>
<p class="sub">The valuation sheet for the scenario selected above: discount factors, present values, terminal value, the bridge from enterprise to equity value, the P/E leg and the blend.</p>
<h4>Discount rate (shared by all scenarios)</h4>{wacc_table(w, inputs)}
{scen_blocks(valuation_section)}

<h2 id="sens">Sensitivities</h2>
{sens_html(sn, out)}

<h2 id="inputs">Assumptions and adjustments</h2>
<h4>Settings</h4>{settings_html}
<h4>Scenario parameters</h4>
<div class="tbl"><table><thead><tr><th></th><th>Bear</th><th>Base</th><th>Bull</th></tr></thead><tbody>
{''.join(f"<tr><th>{lbl}</th>" + ''.join(f"<td class='num'>{fmt(S[k][key])}</td>" for k in SCN) + "</tr>" for lbl, key, fmt in [("Terminal growth", "terminal_growth", lambda x: pc(x, 1)), ("Steady-state ROIC", "steady_roic", lambda x: pc(x, 0)), ("Steady-state operating margin", "steady_margin", lambda x: pc(x, 0)), ("Steady-state tax rate", "steady_tax", lambda x: pc(x, 1)), ("Target multiple", "target_multiple", lambda x: f"{x:.0f}x")])}
</tbody></table></div>
<h4>Adjustments: percentage points added to consensus growth</h4>
<div class="tbl"><table><thead><tr><th>Line</th><th>Period</th><th>Bear</th><th>Base</th><th>Bull</th></tr></thead><tbody>{adj_rows}</tbody></table></div>
<h4>House view</h4>
<p><i>{esc(inputs.get('thesis', {}).get('summary', 'No thesis summary in inputs.json (thesis.summary).'))}</i> Rating: {esc(inputs.get('rating', {}).get('label', '—'))}.</p>

<h2 id="monitor">Monitor</h2>
<h4>Position rules</h4><ul>{rules_html}</ul>
<h4>Live inputs</h4><ul>{live_items}</ul>
<h4>Model checks</h4><ul>{checks_html}</ul>
<h4>Reported quarters since the consensus block</h4>{newq_html}

<h2 id="sources">Sources and method notes</h2>
<ul>
<li>Reported financials: SEC XBRL (sec.company_facts / research_fundamentals through atlas).</li>
<li>Price and beta: Alpaca daily bars through atlas; beta is the 2-year weekly raw beta vs SPY, Bloomberg-adjusted (0.67 × raw + 0.33).</li>
<li>Risk-free: FRED DGS10. ERP: NYU Stern (Damodaran), {pc(inputs['wacc']['erp'])}.</li>
<li>Manual, not available from official sources: the Bloomberg consensus block (dated {a['consensus_date']}), the segment split (press-release tables), the five-year forward P/E range.</li>
<li>Logic: the stock-evaluation skill's <code>valuation_engine.py</code> (a re-implementation of the 美投估值模板 three-scenario method); this folder's <code>inputs.json</code> holds every number; <code>monitor.py</code> refreshes and renders. Markdown twin: reports/{today}.md.</li>
</ul>
<footer>Not investment advice. Generated {today} by the stock-evaluation skill.</footer>
</main>
<script>
const D={payload};
const dark=matchMedia('(prefers-color-scheme: dark)').matches;
const C={{s1:dark?'#3987e5':'#2a78d6',s2:dark?'#d95926':'#eb6834',s3:dark?'#199e70':'#1baf7a',s4:dark?'#c98500':'#eda100',text:dark?'#f0efec':'#0b0b0b',t2:dark?'#c3c2b7':'#52514e',grid:dark?'#3a3936':'#e6e4de',bg:'rgba(0,0,0,0)'}};
const base={{paper_bgcolor:C.bg,plot_bgcolor:C.bg,font:{{color:C.t2,size:12}},margin:{{l:60,r:16,t:40,b:48}},hoverlabel:{{bgcolor:dark?'#242422':'#fff',font:{{color:C.text}}}}}};
const cfg={{displayModeBar:false,responsive:true}};
function targets(id){{
 Plotly.newPlot(id,[
  {{type:'bar',x:D.tgt.names,y:D.tgt.dcf,name:'DCF',marker:{{color:C.s1}},hovertemplate:'%{{x}} DCF $%{{y:,.0f}}<extra></extra>'}},
  {{type:'bar',x:D.tgt.names,y:D.tgt.pe,name:'P/E',marker:{{color:C.s3}},hovertemplate:'%{{x}} P/E $%{{y:,.0f}}<extra></extra>'}},
  {{type:'scatter',mode:'markers+text',x:D.tgt.names,y:D.tgt.blend,name:'Blended',marker:{{color:C.text,size:10,symbol:'diamond'}},text:D.tgt.blend.map(v=>'$'+Math.round(v)),textposition:'top center',textfont:{{color:C.text}},hovertemplate:'%{{x}} blended $%{{y:,.0f}}<extra></extra>'}}],
  {{...base,title:{{text:'12-month targets by method, against today\\'s price',font:{{size:14,color:C.text}},x:0}},barmode:'group',bargap:0.3,bargroupgap:0.06,legend:{{orientation:'h',y:-0.16}},
   yaxis:{{gridcolor:C.grid,zeroline:false,tickprefix:'$',range:[0,Math.max(...D.tgt.blend,...D.tgt.dcf,...D.tgt.pe,D.price)*1.2]}},xaxis:{{showgrid:false}},
   shapes:[{{type:'line',x0:-0.5,x1:3.5,y0:D.price,y1:D.price,line:{{color:C.s2,width:2,dash:'dot'}}}}],
   annotations:[{{x:3.5,y:D.price,xanchor:'right',yanchor:'bottom',text:'price $'+D.price.toFixed(0),showarrow:false,font:{{color:C.s2}}}}]}},cfg);
}}
targets('c_tgt_top'); targets('c_tgt');
Plotly.newPlot('c_fc',[
 {{type:'bar',x:D.fc.labels,y:D.fc.bear.map(v=>v/1000),name:'Bear',marker:{{color:C.s2}},hovertemplate:'%{{x}} bear $%{{y:,.1f}}bn<extra></extra>'}},
 {{type:'bar',x:D.fc.labels,y:D.fc.base.map(v=>v/1000),name:'Base',marker:{{color:C.s1}},hovertemplate:'%{{x}} base $%{{y:,.1f}}bn<extra></extra>'}},
 {{type:'bar',x:D.fc.labels,y:D.fc.bull.map(v=>v/1000),name:'Bull',marker:{{color:C.s3}},hovertemplate:'%{{x}} bull $%{{y:,.1f}}bn<extra></extra>'}}],
 {{...base,title:{{text:'Unlevered free cash flow by fiscal year, $bn (first column is the full current year; the DCF uses its second half)',font:{{size:14,color:C.text}},x:0}},barmode:'group',bargap:0.25,legend:{{orientation:'h',y:-0.22}},
  yaxis:{{gridcolor:C.grid,zerolinecolor:C.t2,tickprefix:'$',ticksuffix:'bn'}},xaxis:{{showgrid:false,tickangle:-45}},
  shapes:[{{type:'rect',xref:'x',yref:'paper',x0:-0.5,x1:D.fc.stage.lastIndexOf('explicit')+0.5,y0:0,y1:1,fillcolor:C.s1,opacity:0.07,line:{{width:0}}}}],
  annotations:[{{x:D.fc.stage.lastIndexOf('explicit')/2,y:1,yref:'paper',text:'explicit (consensus)',showarrow:false,font:{{color:C.t2,size:11}},yanchor:'bottom'}},{{x:D.fc.stage.lastIndexOf('explicit')+1+(D.fc.labels.length-D.fc.stage.lastIndexOf('explicit')-1)/2,y:1,yref:'paper',text:'transition to steady state',showarrow:false,font:{{color:C.t2,size:11}},yanchor:'bottom'}}]}},cfg);
Plotly.newPlot('c_rev',[
 {{type:'bar',x:D.rev.labels,y:D.rev.rev.map(v=>v/1000),name:'Revenue',marker:{{color:D.rev.labels.map((_,i)=>i<D.rev.n_hist?C.t2:C.s1)}},hovertemplate:'%{{x}} revenue $%{{y:,.0f}}bn<extra></extra>'}},
 {{type:'bar',x:D.rev.labels,y:D.rev.capex.map(v=>v/1000),name:'Capex',marker:{{color:D.rev.labels.map((_,i)=>i<D.rev.n_hist?C.grid:C.s2)}},hovertemplate:'%{{x}} capex $%{{y:,.0f}}bn<extra></extra>'}}],
 {{...base,title:{{text:'Base case: revenue and capex, $bn (grey = reported)',font:{{size:14,color:C.text}},x:0}},barmode:'group',bargap:0.2,legend:{{orientation:'h',y:-0.22}},yaxis:{{gridcolor:C.grid,zeroline:false,tickprefix:'$',ticksuffix:'bn'}},xaxis:{{showgrid:false,tickangle:-45}}}},cfg);
Plotly.newPlot('c_pe',[
 {{type:'scatter',mode:'lines',x:[D.pe.low,D.pe.high],y:[0,0],line:{{color:C.grid,width:6}},hoverinfo:'skip',showlegend:false}},
 {{type:'scatter',mode:'markers+text',x:[D.pe.low,D.pe.avg,D.pe.high],y:[0,0,0],text:['5y low '+D.pe.low+'x','5y average '+D.pe.avg+'x','5y high '+D.pe.high+'x'],textposition:['bottom center','bottom center','bottom center'],marker:{{color:C.t2,size:10}},hoverinfo:'skip',showlegend:false}},
 {{type:'scatter',mode:'markers+text',x:[D.pe.now],y:[0],text:['price today '+D.pe.now.toFixed(1)+'x'],textposition:'top center',marker:{{color:C.s2,size:12,symbol:'diamond'}},hoverinfo:'skip',showlegend:false}},
 {{type:'scatter',mode:'markers+text',x:[D.pe.bear,D.pe.base,D.pe.bull],y:[0.35,0.35,0.35],text:['bear '+D.pe.bear+'x','base '+D.pe.base+'x','bull '+D.pe.bull+'x'],textposition:'top center',marker:{{color:[C.s2,C.s1,C.s3],size:11,symbol:'star'}},hoverinfo:'skip',showlegend:false}}],
 {{...base,margin:{{l:20,r:20,t:40,b:20}},title:{{text:'Forward P/E: own five-year range, today\\'s price, and the scenario targets',font:{{size:14,color:C.text}},x:0}},
  xaxis:{{range:[Math.min(D.pe.low,D.pe.now,D.pe.bear)-2,Math.max(D.pe.high,D.pe.now,D.pe.bull)+2],ticksuffix:'x',showgrid:false,zeroline:false}},yaxis:{{visible:false,range:[-0.6,0.9]}}}},cfg);
document.querySelectorAll('.toggle button').forEach(bt=>bt.addEventListener('click',()=>{{
 const k=bt.dataset.scn;
 document.querySelectorAll('.toggle button').forEach(b=>b.classList.toggle('on',b.dataset.scn===k));
 document.querySelectorAll('.scn').forEach(d=>{{d.hidden=d.dataset.scn!==k}});
}}));
</script></body></html>"""
