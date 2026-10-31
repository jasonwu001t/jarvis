"""Thesis tracker: a daily page (reports/thesis.html) that keeps the investment thesis honest.

Three things the valuation report does not do:
  1. Claims board   — every thesis claim in inputs.json (`thesis.claims`) scored against the latest filed numbers
                      (auto checks: yoy / margin / ratio / level on the lines) or carried by hand (status, evidence,
                      as_of, optional due date), with staleness flags.
  2. Assumption impact — how much each assumption moves the house target (tornado: low / high setting), and the
                      break-even value of each single assumption at which the house target equals the price.
  3. Run history    — reports/history.jsonl, one record per run; the page shows what changed since the previous run
                      (price, target, attribution of the target change to market inputs vs model inputs, claim status
                      changes, new quarters) and the target band against the price over time.

Called by monitor.py after each run (never raises into the monitor); standard library only, Plotly via CDN.
Python 3.9 compatible.
"""
from __future__ import annotations

import copy
import datetime as dt
import html as H
import json
import os

import valuation_engine as mm

SCN = ("bear", "base", "bull")
STATUS_LABEL = {"on_track": "On track", "watch": "Watch", "broken": "Broken", "pending": "Pending", "review": "Review"}

# default step for each assumption in the tornado; a ticker overrides any of them in thesis.tornado_steps
DEFAULT_STEPS = {"growth_pp": 0.05, "margin_pp": 0.03, "steady_margin": 0.04, "steady_roic": 0.05, "multiple_rel": 0.20,
                 "terminal_growth": 0.01, "beta": 0.30, "wacc_pp": 0.01, "risk_free": 0.005, "dilution": 0.19}


def esc(s) -> str:
    return H.escape(str(s))


def usd(x, d=0):
    return "—" if x is None else (f"-${-x:,.{d}f}" if x < 0 else f"${x:,.{d}f}")


def pc(x, d=1, sign=False):
    return "—" if x is None else f"{x * 100:{'+' if sign else ''}.{d}f}%"


# ------------------------------------------------------------------------------------------ fast house target
def _targets(inp: dict) -> dict:
    """bear/base/bull blended targets and the house target without the reverse-DCF solves (fast)."""
    m = mm.Model(inp)
    w = m.wacc()
    m.anchor_roic(w)
    t = {}
    for scn in SCN:
        s = m.scenario_series(scn)
        e = m.extrapolate(scn, s)
        t[scn] = m.blend_target(m.dcf(scn, s, e, w)["target"], m.multiples(scn, s)["target"])
    p = inp["blend"]["target_position"]
    house = t["base"] + p * (t["bull"] - t["base"]) if p >= 0 else t["base"] + p * (t["base"] - t["bear"])
    return {**t, "house": house, "wacc": w["wacc"]}


def _forecast_periods(inp: dict) -> list:
    m = mm.Model(inp)
    return m.fc_quarters + [m.fy1, m.fy2] + m.extra_years


def _perturb(inp: dict, name: str, x: float) -> dict:
    """Return a copy of inputs with one assumption moved by x (signed)."""
    d = copy.deepcopy(inp)
    S, W = d["scenarios"], d["wacc"]
    if name == "growth_pp":
        d["adjustments"] += [{"line": "Total revenue", "period_key": k, "bear": x, "base": x, "bull": x} for k in _forecast_periods(inp)]
    elif name == "margin_pp":
        d["adjustments"] += [{"line": "Operating margin", "period_key": k, "bear": x, "base": x, "bull": x} for k in _forecast_periods(inp)]
    elif name in ("steady_margin", "steady_roic", "terminal_growth"):
        for k in SCN:
            S[k][name] = S[k][name] + x
    elif name == "multiple_rel":
        for k in SCN:
            S[k]["target_multiple"] = S[k]["target_multiple"] * (1 + x)
            if "exit_pe" in S[k]:
                S[k]["exit_pe"] = S[k]["exit_pe"] * (1 + x)
    elif name == "beta":
        if W.get("mode") == "manual":
            W["value"] = W["value"] + x * DEFAULT_STEPS["wacc_pp"] / DEFAULT_STEPS["beta"]
        else:
            W["beta"] = W["beta"] + x
    elif name == "risk_free":
        W["risk_free"] = W["risk_free"] + x
        if W.get("mode") == "manual":
            W["value"] = W["value"] + x
    elif name == "dilution":
        latest = d["as_of"]["latest_reported_fy"] * 10 + d["as_of"]["latest_reported_q"]
        sh = d["lines"].get("diluted_shares", {})
        for k, v in list(sh.items()):
            if v is not None and int(k) >= latest:
                sh[k] = v * (1 + x)
        if d["market"].get("shares_override"):
            d["market"]["shares_override"] = d["market"]["shares_override"] * (1 + x)
    elif name == "dcf_weight":
        d["blend"]["dcf_weight"] = x
    return d


def _solve(f, target: float, lo: float, hi: float, n: int = 36):
    flo, fhi = f(lo) - target, f(hi) - target
    if flo * fhi > 0:
        return None
    for _ in range(n):
        mid = (lo + hi) / 2
        fm = f(mid) - target
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


def assumption_impact(inp: dict, price: float, steps: dict = None) -> list:
    """Tornado rows: for each assumption the house target at the low and high setting, and the break-even value."""
    st = {**DEFAULT_STEPS, **(steps or {})}
    base = _targets(inp)
    h0 = base["house"]
    S, W = inp["scenarios"], inp["wacc"]
    manual_wacc = W.get("mode") == "manual"
    rows = []

    def house_at(name, x):
        return _targets(_perturb(inp, name, x))["house"]

    spec = [
        ("growth_pp", "Revenue growth, every forecast period", lambda x: f"{x * 100:+.0f}pp", st["growth_pp"], (-0.30, 0.30), lambda v: f"{v * 100:+.1f}pp vs the street"),
        ("margin_pp", "Operating margin, every forecast period", lambda x: f"{x * 100:+.0f}pp", st["margin_pp"], (-0.25, 0.25), lambda v: f"{v * 100:+.1f}pp vs the street"),
        ("steady_margin", "Steady-state operating margin", lambda x: f"{x * 100:+.0f}pp", st["steady_margin"], (0.03 - S["base"]["steady_margin"], 0.70 - S["base"]["steady_margin"]), lambda v: pc(S["base"]["steady_margin"] + v, 1) + " (base)"),
        ("steady_roic", "Steady-state ROIC", lambda x: f"{x * 100:+.0f}pp", st["steady_roic"], (-S["base"]["steady_roic"] + 0.06, 1.5), lambda v: pc(S["base"]["steady_roic"] + v, 1) + " (base)"),
        ("multiple_rel", "Target multiple (and exit P/E)", lambda x: f"{x * 100:+.0f}%", st["multiple_rel"], (-0.9, 3.0), lambda v: f"{S['base']['target_multiple'] * (1 + v):.1f}x (base)"),
        ("terminal_growth", "Terminal growth", lambda x: f"{x * 100:+.1f}pp", st["terminal_growth"], (-S["base"]["terminal_growth"] + 0.001, min(0.06, base["wacc"] - S["base"]["terminal_growth"] - 0.01)), lambda v: pc(S["base"]["terminal_growth"] + v, 1)),
        ("beta", "WACC (manual)" if manual_wacc else "Beta (cost of equity)", (lambda x: f"{x * 100:+.1f}pp") if manual_wacc else (lambda x: f"{x:+.2f}"), st["wacc_pp"] / DEFAULT_STEPS["wacc_pp"] * DEFAULT_STEPS["beta"] if manual_wacc else st["beta"], (-1.2, 3.0), (lambda v: pc(W.get("value", 0) + v * DEFAULT_STEPS["wacc_pp"] / DEFAULT_STEPS["beta"], 2)) if manual_wacc else (lambda v: f"β {W['beta'] + v:.2f}")),
        ("risk_free", "Ten-year yield (rate-aware multiple too)", lambda x: f"{x * 100:+.2f}pp", st["risk_free"], (-0.04, 0.06), lambda v: pc(W["risk_free"] + v, 2)),
        ("dilution", "Share count", lambda x: f"{x * 100:+.0f}%", st["dilution"], (0.0, 2.0), lambda v: f"{v * 100:+.0f}% shares"),
    ]
    for name, label, fmt, step, (lo, hi), be_fmt in spec:
        if name == "dilution":
            low, high, lo_lbl, hi_lbl = h0, house_at(name, step), "as is", fmt(step)
        else:
            low, high, lo_lbl, hi_lbl = house_at(name, -step), house_at(name, step), fmt(-step), fmt(step)
        be = _solve(lambda x: house_at(name, x), price, lo, hi) if hi > lo else None
        rows.append({"name": name, "label": label, "low": low, "high": high, "low_label": lo_lbl, "high_label": hi_lbl,
                     "swing": abs(high - low), "break_even": be, "break_even_label": be_fmt(be) if be is not None else ("none: more shares only lower the target" if name == "dilution" else "not reachable in the solve range")})
    # method weight: P/E only vs DCF only
    rows.append({"name": "dcf_weight", "label": "Method weight", "low": _targets(_perturb(inp, "dcf_weight", 0.0))["house"],
                 "high": _targets(_perturb(inp, "dcf_weight", 1.0))["house"], "low_label": "P/E only", "high_label": "DCF only",
                 "swing": None, "break_even": None, "break_even_label": "—"})
    for r in rows:
        if r["swing"] is None:
            r["swing"] = abs(r["high"] - r["low"])
    rows.sort(key=lambda r: -r["swing"])
    return rows


# ------------------------------------------------------------------------------------------------- claims
def _latest_key(inp: dict) -> int:
    a = inp["as_of"]
    return a["latest_reported_fy"] * 10 + a["latest_reported_q"]


MODEL_METRICS = {
    # claim-kind target_vs_model: what "model" may name, and where the base-case value lives
    "revenue_cagr_5y": lambda out, inp: out["scenarios"]["base"].get("revenue_cagr_5y"),
    "q5_q8_operating_margin": lambda out, inp: out["scenarios"]["base"].get("q5_q8_operating_margin"),
    "steady_margin": lambda out, inp: inp["scenarios"]["base"].get("steady_margin"),
    "steady_roic": lambda out, inp: inp["scenarios"]["base"].get("steady_roic"),
    "q5_q8_eps": lambda out, inp: out["scenarios"]["base"]["multiples"].get("q5_q8_eps"),
}


def evaluate_claims(inp: dict, model_inputs: dict, out: dict, today: dt.date, rules_eval: list = None,
                    live: dict = None, targets: dict = None) -> list:
    """Score thesis.claims. Auto checks read the lines of model_inputs (history extended with newly filed quarters);
    `filing_event` reads live["filings"] (the monitor's sec.submissions pull); `target_vs_model` reads the folder's
    source/company_targets.json."""
    L = model_inputs["lines"]
    filings = ((live or {}).get("filings") or {}).get("rows") or []
    latest = _latest_key(model_inputs)
    bs_date = dt.date.fromisoformat(inp["as_of"]["balance_sheet_date"])
    res = []
    for c in inp.get("thesis", {}).get("claims", []):
        r = {"id": c.get("id"), "side": c.get("side", "buy"), "weight": c.get("weight", "strong"), "claim": c.get("claim", ""),
             "evidence": c.get("evidence", ""), "as_of": c.get("as_of"), "due": c.get("due"), "source": c.get("source", ""),
             "status": c.get("status", "pending"), "metric": None, "auto": False}
        chk = c.get("check")
        if chk:
            r["auto"] = True
            key = int(chk.get("period_key") or latest)
            v = lambda line, k=key: L.get(line, {}).get(str(k))
            kind = chk.get("kind")
            val = None
            try:
                if kind == "yoy":
                    a, b = v(chk["line"]), v(chk["line"], key - 10)
                    val = a / b - 1 if (a is not None and b) else None
                elif kind in ("margin", "ratio"):
                    a, b = v(chk["num"]), v(chk["den"])
                    val = a / b if (a is not None and b) else None
                elif kind == "level":
                    val = v(chk["line"])
                elif kind == "rule":
                    fired = {r["name"] for r in (rules_eval or []) if r.get("fired")}
                    hit = chk.get("name") in fired
                    r["status"] = (chk.get("when_fired", "broken") if hit else chk.get("when_clear", "on_track"))
                    r["metric"] = f"rule '{chk.get('name')}' {'fired' if hit else 'did not fire'} this run"
                    r["as_of"] = today.isoformat()
                    res.append(r)
                    continue
                elif kind == "filing_event":
                    # a material filing after the claim's date flips it to Review (or `when_filed`); otherwise the manual status stands
                    items = set(chk.get("items") or [])
                    forms = set(chk.get("forms") or (("8-K", "8-K/A") if items else ("6-K",)))
                    since = str(chk.get("since") or c.get("as_of") or inp["as_of"]["balance_sheet_date"])
                    match = [f for f in filings if f["form"] in forms and (not items or items & set(f["items"]))]
                    hits = [f for f in match if f["date"] > since]
                    label = ", ".join(sorted(items)) if items else "/".join(sorted(forms))
                    if not filings:
                        r["metric"] = f"filings feed not available this run (items {label})"
                    elif hits:
                        r["status"] = chk.get("when_filed", "review")
                        r["metric"] = f"{len(hits)} filing{'s' if len(hits) > 1 else ''} since {since}: " + "; ".join(
                            (f"{f['date']} {f['form']} {', '.join(f['items']) or ''}".strip() + (f" — {f['headline'][:90]}…" if f.get("headline") else ""))
                            for f in hits[:4])
                        r["events"] = hits[:4]
                    else:
                        last = match[0]["date"] if match else None
                        r["metric"] = f"no {label} filed since {since}" + (f" (last {last})" if last else "")
                    res.append(r)
                    continue
                elif kind == "consensus_revision":
                    # Nasdaq EPS consensus for the next report date: its change over the window against min / max (fractions)
                    cn = ((live or {}).get("consensus") or {}).get("next") or {}
                    ch = cn.get("change") or {}
                    if not cn or ch.get("pct") is None:
                        r["status"], r["metric"] = "pending", "no consensus history for the next report date" if not cn else f"consensus {cn.get('latest', {}).get('eps_forecast')} with no measurable change yet"
                    else:
                        val, lo, hi, tol = ch["pct"], chk.get("min"), chk.get("max"), chk.get("tolerance", 0.5)
                        ok = (lo is None or val >= lo) and (hi is None or val <= hi)
                        near = (not ok) and ((lo is not None and val >= lo - tol * abs(lo)) or (hi is not None and val <= hi + tol * abs(hi)))
                        r["status"] = "on_track" if ok else ("watch" if near else "broken")
                        r["metric"] = (f"{ch['days']}-day change {val:+.1%} ({ch['from']} → {ch['to']}, {cn.get('latest', {}).get('estimates')} estimates, "
                                       f"{cn.get('revisions', 0)} revisions since {str(cn.get('first', {}).get('captured_at', ''))[:10]}) for {cn.get('report_date')}"
                                       + (f"; min {lo:+.1%}" if lo is not None else "") + (f"; max {hi:+.1%}" if hi is not None else ""))
                    r["as_of"] = today.isoformat()
                    res.append(r)
                    continue
                elif kind == "target_vs_model":
                    tg = ((targets or {}).get("metrics") or {}).get(chk.get("target")) or {}
                    getter = MODEL_METRICS.get(chk.get("model"))
                    mv = getter(out, inp) if getter else None
                    src = (targets or {}).get("source") or {}
                    tol = chk.get("tolerance", 0.05)
                    if mv is None or not tg:
                        r["status"], r["metric"] = "pending", f"no company target '{chk.get('target')}' or model metric '{chk.get('model')}'"
                    else:
                        lo_t, hi_t = tg.get("min"), tg.get("max")
                        ok = (lo_t is None or mv >= lo_t) and (hi_t is None or mv <= hi_t)
                        near = (not ok) and ((lo_t is not None and mv >= lo_t * (1 - tol)) or (hi_t is not None and mv <= hi_t * (1 + tol)))
                        r["status"] = "on_track" if ok else ("watch" if near else "broken")
                        fmtv = (lambda x: pc(x, 1)) if abs(mv) < 3 else (lambda x: f"{x:,.2f}")
                        tgt_txt = " · ".join([f"≥ {fmtv(lo_t)}" if lo_t is not None else "", f"≤ {fmtv(hi_t)}" if hi_t is not None else ""]).strip(" ·")
                        r["metric"] = f"model base {fmtv(mv)} vs company target {tgt_txt} ({esc(src.get('title', 'company target'))}, {esc(src.get('published', ''))}{', unverified' if src.get('verified') is False else ''})"
                    r["as_of"] = src.get("published") or r["as_of"]
                    res.append(r)
                    continue
                elif kind == "qoq":
                    prev = key - 1 if key % 10 > 1 else (key // 10 - 1) * 10 + 4
                    a, b = v(chk["line"]), v(chk["line"], prev)
                    val = a / b - 1 if (a is not None and b) else None
            except (TypeError, ZeroDivisionError):
                val = None
            fmt = chk.get("format", "pct")
            show = (lambda x: pc(x, 1)) if fmt == "pct" else (lambda x: f"{x:,.0f}")
            lo, hi, tol = chk.get("min"), chk.get("max"), chk.get("tolerance", 0.10)
            if val is None:
                r["status"], r["metric"] = "pending", f"no {kind} value for FY{key // 10} Q{key % 10}" if key % 10 else f"no value for FY{key // 10}"
            else:
                ok = (lo is None or val >= lo) and (hi is None or val <= hi)
                near = False
                if not ok:
                    ref = lo if (lo is not None and val < lo) else hi
                    # the band is tolerance x the threshold; at a zero threshold (break-even, flat q/q) the tolerance is the band itself
                    near = ref is not None and abs(val - ref) <= (tol * abs(ref) if abs(ref) > 1e-9 else tol)
                r["status"] = "on_track" if ok else ("watch" if near else "broken")
                thr = " · ".join([f"min {show(lo)}" if lo is not None else "", f"max {show(hi)}" if hi is not None else ""]).strip(" ·")
                r["metric"] = f"{show(val)} in FY{key // 10} Q{key % 10} ({thr})" if key % 10 else f"{show(val)} in FY{key // 10} ({thr})"
            r["as_of"] = inp["as_of"]["balance_sheet_date"]
        else:
            # manual claim: flag for review when a due date has passed or the note predates the latest filing
            try:
                asof = dt.date.fromisoformat(r["as_of"]) if r["as_of"] else None
            except ValueError:
                asof = None
            due = None
            try:
                due = dt.date.fromisoformat(r["due"]) if r["due"] else None
            except ValueError:
                pass
            if due and today >= due and (asof is None or asof < due):
                r["status"], r["metric"] = "review", f"due {due.isoformat()} has passed; update the evidence"
            elif asof and asof < bs_date:
                r["metric"] = f"note from {asof.isoformat()}, before the latest filing ({bs_date.isoformat()})"
        res.append(r)
    return res


# ------------------------------------------------------------------------------------------------ history
def _hist_path(folder: str) -> str:
    return os.path.join(folder, "reports", "history.jsonl")


def load_history(folder: str) -> list:
    p = _hist_path(folder)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def record(inp: dict, out: dict, live: dict, claims: list, today: str) -> dict:
    s, h = out["scenarios"], out["house"]
    P = (live.get("position") or {}).get("result") or {}
    fired = [r["name"] for r in (live.get("_rules") or []) if r.get("fired")]
    return {"date": today, "price": out["price"], "price_date": inp["market"].get("price_date"),
            "risk_free": inp["wacc"].get("risk_free"), "beta": inp["wacc"].get("beta"), "wacc": out["wacc"]["wacc"],
            "rf_date": (live.get("dgs10") or {}).get("date"), "rf_source": (live.get("dgs10") or {}).get("source"),
            "eps_consensus": (((live.get("consensus") or {}).get("next") or {}).get("latest") or {}).get("eps_forecast"),
            "eps_consensus_report_date": ((live.get("consensus") or {}).get("next") or {}).get("report_date"),
            "beta_to": (live.get("beta") or {}).get("to"),
            "bear": s["bear"]["blended_target"], "base": s["base"]["blended_target"], "bull": s["bull"]["blended_target"],
            "house": h["target"], "upside": h["upside"], "expected": (out.get("expected") or {}).get("expected_target"),
            "exposure": P.get("recommended"), "rules": fired, "latest_key": _latest_key(inp),
            "consensus_date": inp["as_of"].get("consensus_date"), "claims": {c["id"]: c["status"] for c in claims if c.get("id")}}


def save_history(folder: str, hist: list, rec: dict) -> list:
    hist = [r for r in hist if r.get("date") != rec["date"]] + [rec]
    os.makedirs(os.path.dirname(_hist_path(folder)), exist_ok=True)
    with open(_hist_path(folder), "w", encoding="utf-8") as fh:
        for r in hist:
            fh.write(json.dumps(r, default=str) + "\n")
    return hist


def changes_since(inp: dict, rec: dict, prev: dict, claims: list) -> dict:
    """What moved since the previous run, with the house-target change split into market inputs (rf, beta) and the rest."""
    if not prev:
        return {}
    d = {"prev_date": prev["date"], "d_price": rec["price"] - prev["price"], "d_house": rec["house"] - prev["house"],
         "d_rf": (rec["risk_free"] or 0) - (prev.get("risk_free") or 0), "d_beta": (rec["beta"] or 0) - (prev.get("beta") or 0),
         "d_wacc": rec["wacc"] - prev["wacc"], "new_quarter": rec["latest_key"] != prev.get("latest_key"),
         "consensus_changed": rec["consensus_date"] != prev.get("consensus_date")}
    try:
        inp2 = copy.deepcopy(inp)
        if prev.get("risk_free") is not None and inp2["wacc"].get("mode") != "manual":
            inp2["wacc"]["risk_free"] = prev["risk_free"]
        if prev.get("beta") is not None and inp2["wacc"].get("mode") != "manual":
            inp2["wacc"]["beta"] = prev["beta"]
        with_prev_rates = _targets(inp2)["house"]
        d["d_house_market"] = rec["house"] - with_prev_rates
        d["d_house_model"] = d["d_house"] - d["d_house_market"]
    except Exception:  # noqa: BLE001
        d["d_house_market"] = d["d_house_model"] = None
    pc_ = prev.get("claims") or {}
    d["claim_changes"] = [(c["id"], pc_.get(c["id"]), c["status"]) for c in claims if c.get("id") and pc_.get(c["id"]) not in (None, c["status"])]
    d["exposure_from"], d["exposure_to"] = prev.get("exposure"), rec["exposure"]
    if (rec.get("eps_consensus") is not None and prev.get("eps_consensus") is not None
            and rec.get("eps_consensus_report_date") == prev.get("eps_consensus_report_date")
            and abs(rec["eps_consensus"] - prev["eps_consensus"]) > 1e-9):
        d["consensus_move"] = {"report_date": rec["eps_consensus_report_date"], "from": prev["eps_consensus"], "to": rec["eps_consensus"]}
    return d


# --------------------------------------------------------------------------------------------------- page
CSS = """
:root{color-scheme:light dark;--surface:#fcfcfb;--surface-2:#f1f0ec;--text:#0b0b0b;--text-2:#52514e;--muted:#8a8882;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--good:#008300;--warn:#b87a00;--bad:#c73c3b;--line:#dcdad4;--hl:#fff3cc}
@media (prefers-color-scheme:dark){:root{--surface:#1a1a19;--surface-2:#242422;--text:#f0efec;--text-2:#c3c2b7;--muted:#8d8c85;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--good:#3ecf8e;--warn:#e0a52a;--bad:#e66767;--line:#3a3936;--hl:#3b3416}}
*{box-sizing:border-box} body{margin:0;background:var(--surface);color:var(--text);font:15px/1.55 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif}
nav{position:sticky;top:0;z-index:5;background:var(--surface);border-bottom:1px solid var(--line);padding:8px 16px;display:flex;gap:4px;overflow-x:auto;white-space:nowrap}
nav a{color:var(--text-2);text-decoration:none;padding:6px 10px;border-radius:999px;font-size:13px} nav a:hover{background:var(--surface-2);color:var(--text)}
main{max-width:1180px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.01em} h2{font-size:20px;margin:44px 0 12px;padding-top:8px;border-top:2px solid var(--line)} h3{font-size:16px;margin:20px 0 6px}
p{margin:8px 0} .sub{color:var(--text-2)} small{color:var(--muted)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:14px 0} .tile{background:var(--surface-2);border-radius:10px;padding:12px 14px} .tile .k{font-size:12px;color:var(--text-2)} .tile .v{font-size:24px;font-weight:650;letter-spacing:-.01em} .tile .n{font-size:12px;color:var(--muted)}
.tbl{overflow-x:auto;margin:8px 0 16px;border:1px solid var(--line);border-radius:8px} table{border-collapse:separate;border-spacing:0;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
th,td{padding:6px 9px;border-bottom:1px solid var(--line);text-align:right;vertical-align:top} th:first-child,td:first-child{text-align:left} thead th{background:var(--surface-2);color:var(--text-2);font-weight:600;font-size:12px}
td.l{text-align:left;white-space:normal} td.num{text-align:right;white-space:nowrap} tr.hl td{background:var(--hl)}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.pill.on_track{background:color-mix(in srgb,var(--good) 18%,transparent);color:var(--good)} .pill.watch{background:color-mix(in srgb,var(--warn) 18%,transparent);color:var(--warn)}
.pill.broken{background:color-mix(in srgb,var(--bad) 18%,transparent);color:var(--bad)} .pill.pending,.pill.review{background:var(--surface-2);color:var(--text-2)} .pill.review{color:var(--warn)}
.box{background:var(--surface-2);border-left:4px solid var(--s1);border-radius:10px;padding:12px 16px;margin:12px 0} .box.warn{border-color:var(--warn)} .box.bad{border-color:var(--bad)}
.chart{height:360px;margin:8px 0} .chart.short{height:260px} .charts2{display:grid;grid-template-columns:1fr 1fr;gap:14px} @media(max-width:860px){.charts2{grid-template-columns:1fr}}
ul{padding-left:20px} li{margin:4px 0} footer{margin-top:40px;color:var(--muted);font-size:12px} .good{color:var(--good)} .bad{color:var(--bad)} .warn{color:var(--warn)}
"""


def page(inp: dict, out: dict, live: dict, claims: list, tornado: list, hist: list, chg: dict, today: str, targets: dict = None) -> str:
    tk, co = inp["company"]["ticker"], inp["company"]["name"]
    s, h, price = out["scenarios"], out["house"], out["price"]
    ex, im = out.get("expected") or {}, out.get("implied") or {}
    P = (live.get("position") or {}).get("result") or {}
    fired = [r for r in (live.get("_rules") or []) if r.get("fired") and r.get("exposure") is not None]
    e = live.get("earnings") or {}
    buy = [c for c in claims if c["side"] == "buy"]
    sell = [c for c in claims if c["side"] != "buy"]
    n_on = sum(1 for c in buy if c["status"] == "on_track")
    n_bad = sum(1 for c in buy if c["status"] == "broken")
    risks_live = sum(1 for c in sell if c["status"] in ("broken", "watch"))

    def pill(st):
        return f"<span class='pill {st}'>{STATUS_LABEL.get(st, st)}</span>"

    def claim_rows(cs):
        return "".join(
            f"<tr><td class='l'><b>{esc(c['claim'])}</b>{('<br><small>' + esc(c['evidence']) + '</small>') if c.get('evidence') else ''}</td>"
            f"<td class='l'>{esc(c['weight'])}</td><td class='l'>{pill(c['status'])}</td>"
            f"<td class='l'>{esc(c['metric'] or ('auto check' if c['auto'] else 'manual'))}</td>"
            f"<td class='l'><small>{esc(c.get('as_of') or '—')}{(' · due ' + esc(c['due'])) if c.get('due') else ''}{('<br>' + esc(c['source'])) if c.get('source') else ''}</small></td></tr>"
            for c in cs) or "<tr><td colspan='5' class='l'>none</td></tr>"

    verdict_cls = "bad" if n_bad else ("warn" if any(c["status"] in ("watch", "review") for c in buy) else "")
    verdict = (f"<b>Thesis score:</b> {n_on} of {len(buy)} buy-side claims on track" + (f", <b class='bad'>{n_bad} broken</b>" if n_bad else "") +
               f"; {risks_live} of {len(sell)} sell-side risks live. " +
               (f"Rule <b>{esc(fired[0]['name'])}</b>: {esc(fired[0]['action'])}" if fired else "No position rule fired."))

    # changes box
    # freshness of the live inputs (stale when the yield is more than 4 days old or the beta window ended more than 10 days ago)
    rec_now = hist[-1] if hist else {}
    fresh = []
    try:
        run_d = dt.date.fromisoformat(today)
        for lbl, key, limit in (("price", "price_date", 4), ("10-year", "rf_date", 4), ("beta window", "beta_to", 10)):
            v = rec_now.get(key)
            if not v:
                fresh.append(f"{lbl}: <b class='warn'>not refreshed</b>")
                continue
            age = (run_d - dt.date.fromisoformat(str(v)[:10])).days
            fresh.append(f"{lbl} {esc(v)}" + (f" <b class='warn'>({age} days old)</b>" if age > limit else ""))
    except ValueError:
        pass
    fresh_html = ("<p class='sub'>Live inputs this run: " + " · ".join(fresh) + (f" · yield source {esc(rec_now.get('rf_source'))}" if rec_now.get("rf_source") else "") + "</p>") if fresh else ""
    if chg:
        sgn = lambda x, d=0: ("+" if x >= 0 else "-") + usd(abs(x), d)
        parts = [f"Since <b>{chg['prev_date']}</b>: price {sgn(chg['d_price'], 2)} "
                 f"({pc(chg['d_price'] / (price - chg['d_price']), 1, True) if price != chg['d_price'] else '—'}), "
                 f"house target <b>{sgn(chg['d_house'])}</b>"]
        if chg.get("d_house_market") is not None:
            parts.append(f"of which market inputs (10-year {chg['d_rf'] * 100:+.2f}pp, beta {chg['d_beta']:+.2f} → WACC {chg['d_wacc'] * 100:+.2f}pp) "
                         f"{sgn(chg['d_house_market'])} and model inputs (consensus, actuals, assumptions) {sgn(chg['d_house_model'])}.")
        if chg.get("new_quarter"):
            parts.append("<b>A new quarter is in the history.</b>")
        if chg.get("consensus_changed"):
            parts.append("The consensus block was re-dated.")
        if chg.get("consensus_move"):
            cm = chg["consensus_move"]
            parts.append(f"Nasdaq EPS consensus for {esc(cm['report_date'])} moved {cm['from']:.2f} → <b>{cm['to']:.2f}</b>.")
        if chg.get("claim_changes"):
            parts.append("Claims that changed: " + "; ".join(f"<b>{esc(i)}</b> {STATUS_LABEL.get(a, a)} → {STATUS_LABEL.get(b, b)}" for i, a, b in chg["claim_changes"]) + ".")
        if chg.get("exposure_from") is not None and chg.get("exposure_to") is not None and abs(chg["exposure_from"] - chg["exposure_to"]) > 1e-9:
            parts.append(f"Recommended exposure {pc(chg['exposure_from'], 0)} → <b>{pc(chg['exposure_to'], 0)}</b>.")
        if len(parts) == 1:
            parts.append("Nothing else moved: no new filing, no claim changed status, exposure unchanged.")
        changes_html = f"<div class='box'>{' '.join(parts)}</div>"
    else:
        changes_html = "<div class='box'>First run: the history starts today. From the next run this box says what moved and why.</div>"

    # tornado table
    trows = "".join(
        f"<tr><td class='l'>{esc(r['label'])}</td><td class='num'>{esc(r['low_label'])}</td><td class='num'>{usd(r['low'])}</td>"
        f"<td class='num'>{esc(r['high_label'])}</td><td class='num'>{usd(r['high'])}</td><td class='num'><b>{usd(r['swing'])}</b></td>"
        f"<td class='l'>{esc(r['break_even_label'])}</td></tr>" for r in tornado)

    # history table (last 12 runs)
    hrows = "".join(
        f"<tr{' class=hl' if r['date'] == today else ''}><td class='l'>{esc(r['date'])}</td><td class='num'>{usd(r['price'], 2)}</td><td class='num'>{usd(r['bear'])}</td>"
        f"<td class='num'>{usd(r['base'])}</td><td class='num'>{usd(r['bull'])}</td><td class='num'><b>{usd(r['house'])}</b></td><td class='num'>{pc(r['upside'], 1, True)}</td>"
        f"<td class='num'>{pc(r['wacc'], 2)}</td><td class='num'>{pc(r.get('exposure'), 0) if r.get('exposure') is not None else '—'}</td>"
        f"<td class='l'><small>{esc(', '.join(r.get('rules') or [])) or '—'}</small></td></tr>" for r in reversed(hist[-12:]))

    # material filings (last 120 days) from the monitor's sec.submissions pull
    MATERIAL = ("1.01", "1.02", "2.01", "2.03", "2.05", "2.06", "3.02", "5.02", "8.01")
    frows = ((live.get("filings") or {}).get("rows") or [])
    cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=120)).isoformat()
    mat = [f for f in frows if f["date"] >= cutoff and (f["form"] == "6-K" or set(f["items"]) & set(MATERIAL))][:10]
    if frows:
        filings_html = ("<h3>Material filings, last 120 days</h3><div class='tbl'><table><thead><tr><th>Filed</th><th>Form</th><th>Items</th><th>Document</th></tr></thead><tbody>"
                        + "".join(f"<tr><td class='l'>{esc(f['date'])}</td><td class='l'>{esc(f['form'])}</td><td class='l'>{esc(', '.join(f['items']) or '—')}{('<br><small>' + esc(f['headline'][:160]) + '…</small>') if f.get('headline') else ''}</td>"
                                  f"<td class='l'><a href='{esc(f['url'])}'>{esc((f['url'] or '').rsplit('/', 1)[-1])}</a>" + "".join(f" · <a href='{esc(u)}'>{esc(k)}</a>" for k, u in sorted((f.get('exhibits') or {}).items())[:4]) + "</td></tr>" for f in mat)
                        + ("" if mat else "<tr><td colspan='4' class='l'>none</td></tr>") + "</tbody></table></div>")
    else:
        filings_html = "<p class='sub'>Filings feed not available this run (atlas has no sec.submissions rows for this ticker).</p>"
    tg_html = ""
    if targets:
        src = targets.get("source") or {}
        def _tgt(k, v):
            fmt = (lambda x: pc(x, 0)) if abs(v.get("min") if v.get("min") is not None else v.get("max", 0)) < 3 else (lambda x: f"{x:,.0f}")
            parts = [esc(v.get("label") or k)]
            if v.get("min") is not None:
                parts.append("≥ " + fmt(v["min"]))
            if v.get("max") is not None:
                parts.append("≤ " + fmt(v["max"]))
            return " ".join(parts)
        unverified = ", unverified against a filing" if src.get("verified") is False else ""
        tg_html = ("<p class='sub'>Company targets on file: " + "; ".join(_tgt(k, v) for k, v in (targets.get("metrics") or {}).items())
                   + f" · source: {esc(src.get('title', ''))} ({esc(src.get('published', ''))}{unverified}).</p>")
    due = sorted([c for c in claims if c.get("due")], key=lambda c: c["due"])
    next_html = "".join(f"<li><b>{esc(c['due'])}</b> · {esc(c['claim'])}</li>" for c in due[:6]) or "<li>no dated claims</li>"

    payload = json.dumps({
        "price": price, "house": h["target"],
        "tornado": {"labels": [r["label"] for r in tornado], "low": [r["low"] for r in tornado], "high": [r["high"] for r in tornado],
                    "lo_lbl": [r["low_label"] for r in tornado], "hi_lbl": [r["high_label"] for r in tornado]},
        "hist": {"date": [r["date"] for r in hist], "price": [r["price"] for r in hist], "bear": [r["bear"] for r in hist],
                 "base": [r["base"] for r in hist], "bull": [r["bull"] for r in hist], "house": [r["house"] for r in hist]},
    })
    thesis_summary = inp.get("thesis", {}).get("summary", "")
    rating = inp.get("rating", {}).get("label", "")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(tk)} thesis tracker {today}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>{CSS}</style></head><body>
<nav><a href="#call">Call</a><a href="#claims">Thesis claims</a><a href="#changes">What changed</a><a href="#impact">Assumption impact</a><a href="#history">History</a><a href="#next">Next</a><a href="latest.html">Full valuation report →</a></nav>
<main>
<h1 id="call">{esc(co)} ({esc(tk)}) — thesis tracker</h1>
<p class="sub">Run {today} · price {usd(price, 2)} ({esc(inp['market'].get('price_date'))}) · latest filed quarter FY{inp['as_of']['latest_reported_fy']} Q{inp['as_of']['latest_reported_q']} · consensus block {esc(inp['as_of'].get('consensus_date'))}
{(' · next earnings <b>' + esc(e.get('report_date')) + '</b>') if e.get('report_date') else ''} · {len(hist)} run{'s' if len(hist) != 1 else ''} in the history</p>
<div class="tiles">
<div class="tile"><div class="k">House target</div><div class="v">{usd(h['target'])}</div><div class="n">{pc(h['upside'], 1, True)} vs price</div></div>
<div class="tile"><div class="k">Bear · Base · Bull</div><div class="v">{s['bear']['blended_target']:,.0f} · {s['base']['blended_target']:,.0f} · {s['bull']['blended_target']:,.0f}</div><div class="n">expected {usd(ex.get('expected_target'))}</div></div>
<div class="tile"><div class="k">Recommended exposure</div><div class="v">{pc(P.get('recommended'), 0) if P.get('recommended') is not None else '—'}</div><div class="n">{esc(fired[0]['name']) if fired else 'no rule fired'}</div></div>
<div class="tile"><div class="k">Price implies</div><div class="v">{(f"{im.get('growth_pp') * 100:+.1f}pp growth") if im.get('growth_pp') is not None else '—'}</div><div class="n">or {pc(im.get('steady_margin'), 1)} steady margin</div></div>
<div class="tile"><div class="k">WACC</div><div class="v">{pc(out['wacc']['wacc'], 2)}</div><div class="n">rf {pc(inp['wacc'].get('risk_free'), 2)} · β {inp['wacc'].get('beta', 0):.2f}</div></div>
</div>
<div class="box {verdict_cls}">{verdict}</div>
<p><i>{esc(thesis_summary)}</i></p><p class="sub">{esc(rating)}</p>
<h2 id="claims">Thesis claims</h2>
<p class="sub">Auto-checked claims read the latest filed quarter (SEC XBRL, press-release segment tables keyed into inputs.json); manual claims carry a status, evidence and a date, and are flagged for review when a due date passes or the note predates the latest filing.</p>
<h3>Why own it</h3>
<div class="tbl"><table><thead><tr><th>Claim</th><th>Weight</th><th>Status</th><th>Latest evidence</th><th>As of / source</th></tr></thead><tbody>{claim_rows(buy)}</tbody></table></div>
<h3>What would break it</h3>
<div class="tbl"><table><thead><tr><th>Risk</th><th>Weight</th><th>Status</th><th>Latest evidence</th><th>As of / source</th></tr></thead><tbody>{claim_rows(sell)}</tbody></table></div>
<h2 id="changes">What changed since the last run</h2>
{changes_html}{fresh_html}{filings_html}{tg_html}
<h2 id="impact">Assumption impact on the house target</h2>
<p class="sub">Each assumption moved on its own, everything else held; the house target today is <b>{usd(h['target'])}</b> against a price of {usd(price, 2)}. The last column is the single-assumption break-even: the value at which the house target equals the price.</p>
<div id="c_tornado" class="chart"></div>
<div class="tbl"><table><thead><tr><th>Assumption</th><th>Low setting</th><th>Target</th><th>High setting</th><th>Target</th><th>Swing</th><th>Break-even at the price</th></tr></thead><tbody>{trows}</tbody></table></div>
<h2 id="history">History</h2>
<div id="c_hist" class="chart short"></div>
<div class="tbl"><table><thead><tr><th>Run</th><th>Price</th><th>Bear</th><th>Base</th><th>Bull</th><th>House</th><th>Upside</th><th>WACC</th><th>Exposure</th><th>Rule</th></tr></thead><tbody>{hrows}</tbody></table></div>
<h2 id="next">Next</h2>
<ul>{next_html}</ul>
<p class="sub">After a print: run the monitor with <code>--apply-actuals</code>, key the segment lines and the new guide, update the manual claims' evidence and dates, and re-run. The claims board re-scores itself.</p>
<footer>Not investment advice. Generated {today} by the stock-evaluation skill (scripts/thesis_tracker.py); history in reports/history.jsonl.</footer>
</main>
<script>
const D={payload};
const dark=matchMedia('(prefers-color-scheme: dark)').matches;
const C={{s1:dark?'#3987e5':'#2a78d6',s2:dark?'#d95926':'#eb6834',s3:dark?'#199e70':'#1baf7a',text:dark?'#f0efec':'#0b0b0b',t2:dark?'#c3c2b7':'#52514e',grid:dark?'#3a3936':'#e6e4de'}};
const base={{paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{{color:C.t2,size:12}},margin:{{l:250,r:16,t:36,b:48}}}};
const cfg={{displayModeBar:false,responsive:true}};
const T=D.tornado, labs=T.labels.slice().reverse();
Plotly.newPlot('c_tornado',[
 {{type:'bar',orientation:'h',y:labs,x:T.low.slice().reverse().map(v=>v-D.house),base:D.house,name:'low setting',marker:{{color:C.s2}},text:T.lo_lbl.slice().reverse(),textposition:'inside',insidetextanchor:'middle',textfont:{{color:'#fff',size:11}},hovertemplate:'%{{y}}<br>%{{text}} → $%{{customdata:,.0f}}<extra></extra>',customdata:T.low.slice().reverse()}},
 {{type:'bar',orientation:'h',y:labs,x:T.high.slice().reverse().map(v=>v-D.house),base:D.house,name:'high setting',marker:{{color:C.s3}},text:T.hi_lbl.slice().reverse(),textposition:'inside',insidetextanchor:'middle',textfont:{{color:'#fff',size:11}},hovertemplate:'%{{y}}<br>%{{text}} → $%{{customdata:,.0f}}<extra></extra>',customdata:T.high.slice().reverse()}}],
 {{...base,barmode:'overlay',bargap:0.25,title:{{text:'House target under each assumption\\'s low and high setting (line = price)',font:{{size:14,color:C.text}},x:0}},legend:{{orientation:'h',y:-0.12}},
  xaxis:{{tickprefix:'$',gridcolor:C.grid,zeroline:false}},yaxis:{{automargin:true}},
  shapes:[{{type:'line',x0:D.price,x1:D.price,y0:-0.5,y1:labs.length-0.5,line:{{color:C.text,width:1.5,dash:'dot'}}}},{{type:'line',x0:D.house,x1:D.house,y0:-0.5,y1:labs.length-0.5,line:{{color:C.s1,width:1.5}}}}],
  annotations:[{{x:D.price,y:labs.length-0.5,yanchor:'bottom',text:'price $'+D.price.toFixed(0),showarrow:false,font:{{color:C.text}}}},{{x:D.house,y:-0.5,yanchor:'top',text:'house $'+D.house.toFixed(0),showarrow:false,font:{{color:C.s1}}}}]}},cfg);
const Hh=D.hist;
Plotly.newPlot('c_hist',[
 {{type:'scatter',mode:'lines',x:Hh.date,y:Hh.bull,name:'Bull',line:{{color:C.s3,width:1}},fill:'none'}},
 {{type:'scatter',mode:'lines',x:Hh.date,y:Hh.bear,name:'Bear',line:{{color:C.s2,width:1}},fill:'tonexty',fillcolor:dark?'rgba(57,135,229,0.10)':'rgba(42,120,214,0.08)'}},
 {{type:'scatter',mode:'lines+markers',x:Hh.date,y:Hh.house,name:'House target',line:{{color:C.s1,width:2.5}}}},
 {{type:'scatter',mode:'lines+markers',x:Hh.date,y:Hh.price,name:'Price',line:{{color:C.text,width:2,dash:'dot'}}}}],
 {{...base,margin:{{l:60,r:16,t:36,b:48}},title:{{text:'Target band and price across runs',font:{{size:14,color:C.text}},x:0}},legend:{{orientation:'h',y:-0.2}},yaxis:{{tickprefix:'$',gridcolor:C.grid,zeroline:false}},xaxis:{{showgrid:false,type:'category'}}}},cfg);
</script></body></html>"""


# ---------------------------------------------------------------------------------------------------- entry
def run(inputs: dict, model_inputs: dict, out: dict, live: dict, folder: str, rules_eval: list = None) -> str:
    """Score claims, compute the tornado, append the history, write reports/thesis.html. Returns the page path."""
    today = dt.date.today()
    live = dict(live)
    live["_rules"] = rules_eval or []
    tpath = os.path.join(folder, "source", "company_targets.json")
    targets = None
    if os.path.exists(tpath):
        with open(tpath, encoding="utf-8") as fh:
            targets = json.load(fh)
    claims = evaluate_claims(inputs, model_inputs, out, today, rules_eval, live, targets)
    tornado = assumption_impact(model_inputs, out["price"], (inputs.get("thesis") or {}).get("tornado_steps"))
    hist = load_history(folder)
    prev = next((r for r in reversed(hist) if r.get("date") != today.isoformat()), None)
    rec = record(inputs, out, live, claims, today.isoformat())
    chg = changes_since(model_inputs, rec, prev, claims)
    hist = save_history(folder, hist, rec)
    html = page(inputs, out, live, claims, tornado, hist, chg, today.isoformat(), targets)
    path = os.path.join(folder, "reports", "thesis.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return path
