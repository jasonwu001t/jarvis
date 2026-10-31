"""One place for what the skill reads from atlas (http://127.0.0.1:8000), after the 2026-10-25 pipeline lanes:

  fundamentals(ticker)   /research/fundamentals/{t}?currency=USD   KPI series per fiscal period, USD millions; IFRS filers
                         converted at atlas's FX; per-share values x per_share_divisor (ADR ratio), shares / divisor
  segments(ticker)       /research/fundamentals/{t}/segments        revenue and operating income per business segment
                         (sec.segment_facts, XBRL dimensions; a 6-K filer's split from sec.foreign_quarterly_statements,
                         one axis of it); members with revenue in the latest four quarters
  guidance_releases(t)   sec.earnings_guidance rows per release     next-quarter revenue / operating income, full-year
                         capex / expenses, in the shape guidance.py's collect() returns (beat-adjustment needs history)
  events(ticker)         /filings/ticker/{t}/events                 material 8-K items and 6-Ks with headlines

Every function raises on a transport error and returns an empty structure when atlas has nothing for the ticker, so a
caller can fall back (a folder's segments.py, guidance.py's regexes) and say so. Standard library only; Python 3.9.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

ATLAS = os.environ.get("ATLAS_URL", "http://127.0.0.1:8000").rstrip("/")
PER_SHARE_KPIS = {"dividends_per_share", "eps_diluted", "eps_basic"}
SHARE_KPIS = {"shares_diluted", "shares_basic", "shares_outstanding", "shares_outstanding_cover"}


class NotCollected(Exception):
    """atlas answers 404: the ticker is not on a list (or the dataset has nothing for it)."""


def get(path: str, **params) -> dict:
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(f"{ATLAS}{path}" + (f"?{qs}" if qs else ""), headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise NotCollected(f"{path}: {exc.read()[:200]!r}") from exc
        raise


def period_key(period: str) -> int:
    """'2026-Q3' -> 20263, 'FY2026' -> 20260."""
    if period.startswith("FY"):
        return int(period[2:]) * 10
    y, q = period.split("-Q")
    return int(y) * 10 + int(q)


class NotConverted(RuntimeError):
    """atlas served a money KPI in another currency than the one asked for."""


def fundamentals(ticker: str, currency: str = "USD") -> dict:
    """{'kpis': {id: {period_key: {value, end, filed, form}}}, 'company_type', 'per_share_divisor', 'currency', 'native_unit'}.
    Money in millions of `currency`; per-share values per listed share (x divisor); share counts in millions of listed-share
    equivalents (/ divisor)."""
    d = get(f"/api/v1/research/fundamentals/{ticker}", currency=currency)["data"]
    div = float(d.get("per_share_divisor") or 1.0)
    out = {}
    for k in d.get("kpis", []):
        # A money KPI atlas left in another currency (no FX series for it, or none stored: fx.note says why) must
        # never be read as `currency`: the payload's top-level currency said USD over DKK figures (audit #143).
        money = str(k.get("unit") or "").split("/")[0]
        if len(money) == 3 and money.isalpha() and money.isupper() and money != currency.upper():
            note = (d.get("fx") or {}).get("note") or k.get("fx_note") or "not converted"
            raise NotConverted(f"{ticker} {k['id']} is served in {money}, not {currency}: {note}")
        series = {}
        for row in k.get("quarterly", []) + k.get("annual", []):
            v = row.get("value")
            if v is None:
                continue
            try:
                key = period_key(row["period"])
            except (ValueError, KeyError):
                continue
            if k["id"] in PER_SHARE_KPIS:
                v = v * div
            elif k["id"] in SHARE_KPIS:
                v = v / 1e6 / div
            else:
                v = v / 1e6
            series[key] = {"value": v, "end": row.get("end"), "filed": row.get("filed"), "form": row.get("form"),
                           "fx_rate": row.get("fx_rate"), "native_value": row.get("native_value")}
        out[k["id"]] = series
    return {"kpis": out, "company_type": d.get("company_type", "default"), "per_share_divisor": div,
            "currency": d.get("currency", currency), "native_unit": d.get("native_unit")}


AXIS_PREFERENCE = ("platform", "product")     # a 6-K filer's business lines; geography and technology cut the same revenue


def segments(ticker: str, recent_quarters: int = 4, axis: str = None) -> dict:
    """{'defs': {name: {parent: None, oi_line: 'segoi:<name>' | None}}, 'lines': {'seg:<name>': {key: musd}, 'segoi:<name>': {...}},
    'axis', 'axes', 'members_all', 'latest_keys', 'source'}. A member counts when it has revenue in the latest
    `recent_quarters` quarters its axis reported (the current reporting structure); older or operating-income-only members
    are listed in members_all only. A US filer's members (sec.segment_facts) carry no axis: its one business-segment axis.
    A foreign filer's 6-K members (sec.foreign_quarterly_statements) come on several axes that each cut the same revenue
    (geography, platform, product, technology): one becomes the business lines (`axis`, else platform, else product, else
    any but geography and technology), never their union, so a name on two axes ('Others') cannot overwrite the other
    (audit #142); `axes` lists every axis's members. A name repeated within the axis is told apart by its member_key."""
    d = get(f"/api/v1/research/fundamentals/{ticker}/segments")["data"]
    by_axis = {}
    for m in d.get("segments", []):
        by_axis.setdefault(m.get("axis"), []).append(m)
    if axis is None:
        named = sorted(a for a in by_axis if a)
        axis = next((a for a in AXIS_PREFERENCE if a in by_axis), None) or next((a for a in named if a not in ("geography", "technology")), None)
    members = by_axis.get(axis, [])
    latest_keys = sorted({r["fiscal_year"] * 10 + int(r["fiscal_period"][1]) for m in members
                          for r in m["revenue"]["quarterly"] if r.get("fiscal_period", "").startswith("Q")})[-recent_quarters:]
    defs, lines = {}, {}
    for m in members:
        rq = {r["fiscal_year"] * 10 + int(r["fiscal_period"][1]): r["value"] for r in m["revenue"]["quarterly"] if r.get("fiscal_period", "").startswith("Q") and r.get("value") is not None}
        if not latest_keys or not all(k in rq for k in latest_keys):
            continue
        name = m["member"] if m["member"] not in defs else f"{m['member']} ({m.get('member_key')})"
        for r in m["revenue"]["annual"]:
            if r.get("value") is not None:
                rq[r["fiscal_year"] * 10] = r["value"]
        lines[f"seg:{name}"] = {k: v / 1e6 for k, v in rq.items()}
        oi = {}
        for r in m["operating_income"]["quarterly"]:
            if r.get("fiscal_period", "").startswith("Q") and r.get("value") is not None:
                oi[r["fiscal_year"] * 10 + int(r["fiscal_period"][1])] = r["value"]
        for r in m["operating_income"]["annual"]:
            if r.get("value") is not None:
                oi[r["fiscal_year"] * 10] = r["value"]
        if oi:
            lines[f"segoi:{name}"] = {k: v / 1e6 for k, v in oi.items()}
        defs[name] = {"parent": None, "oi_line": f"segoi:{name}" if oi else None}
    return {"defs": defs, "lines": lines, "axis": axis if axis is not None else d.get("axis"), "members_all": [m["member"] for m in members],
            "axes": {a: [m["member"] for m in ms] for a, ms in by_axis.items() if a}, "latest_keys": latest_keys,
            "source": f"{d.get('source') or 'sec.segment_facts'} via atlas" + (f", {axis} axis" if axis else "")}


def _musd(v, unit):
    return v / 1e6 if unit == "USD" else v


BASIS_RANK = {"gaap": 0, "non_gaap": 2}     # an unstated basis ranks 1


def guidance_releases(ticker: str, since: str = None) -> list:
    """Every parsed guidance row grouped per release, newest last, in guidance.py's shape:
    [{date, accession, revenue_next_quarter: {period_key, low, high, mid, unit, basis, source_text}, operating_income_next_quarter,
      capex_full_year, expenses_full_year, gross_margin_next_quarter, operating_margin_next_quarter, parsed: True}].
    Where a release states a metric on more than one basis, the GAAP row is kept."""
    params = {"eq.ticker": ticker, "limit": 2000}
    if since:
        params["start"] = since
    d = get("/api/v1/data/datasets/sec.earnings_guidance/rows", **params)["data"]
    cols = [c["name"] for c in d["columns"]]
    rows = [dict(zip(cols, r)) if isinstance(r, list) else r for r in d["rows"]]
    by = {}
    for r in rows:
        acc = r["accession_number"]
        g = by.setdefault(acc, {"accession": acc, "date": str(r.get("knowledge_time") or "")[:10], "parsed": True})
        pk = r.get("period_key")
        if pk is None and r.get("fiscal_year"):
            pk = int(r["fiscal_year"]) * 10 + int(r.get("fiscal_quarter") or 0)
        if pk is None:
            continue
        val = {"period_key": int(pk), "low": _musd(r["low"], r["unit"]), "high": _musd(r["high"], r["unit"]), "mid": _musd(r["mid"], r["unit"]),
               "unit": r["unit"], "basis": r.get("basis"), "source_text": r.get("source_text")}
        kind = r.get("period_kind")
        name = {("revenue", "next_quarter"): "revenue_next_quarter", ("operating_income", "next_quarter"): "operating_income_next_quarter",
                ("capex", "fiscal_year"): "capex_full_year", ("opex", "fiscal_year"): "expenses_full_year",
                ("gross_margin", "next_quarter"): "gross_margin_next_quarter", ("operating_margin", "next_quarter"): "operating_margin_next_quarter",
                ("eps", "next_quarter"): "eps_next_quarter", ("tax_rate", "next_quarter"): "tax_rate_next_quarter"}.get((r.get("metric"), kind))
        # One row per metric and period kind: GAAP over an unstated basis over non-GAAP, whatever the row order (MU
        # states eps and gross margin on both); the kept row's basis says which (audit #93).
        if name and (name not in g or BASIS_RANK.get(val["basis"], 1) < BASIS_RANK.get(g[name]["basis"], 1)):
            g[name] = val
    out = sorted(by.values(), key=lambda g: g["date"])
    return out


def events(ticker: str, limit: int = 200, items: str = None, since: str = None) -> dict:
    """Material filings in the monitor's shape: {'rows': [{date, form, items: [...], accession, url, headline, item_title,
    exhibits: {type: url}, knowledge_time}], 'n', 'source'}; rows grouped per filing, newest first."""
    d = get(f"/api/v1/filings/ticker/{ticker}/events", limit=limit, items=items, since=since)["data"]
    by = {}
    for e in d.get("events", []):
        acc = e["accession_number"]
        row = by.setdefault(acc, {"date": e["filing_date"], "form": e["form"], "items": [], "accession": acc, "url": e.get("primary_doc_url"),
                                  "headline": "", "item_title": "", "exhibits": {}, "knowledge_time": e.get("accepted_at")})
        if e.get("item") and e["item"] not in row["items"]:
            row["items"].append(e["item"])
        if e.get("headline") and not row["headline"]:
            row["headline"], row["item_title"] = e["headline"], e.get("item_title") or ""
        ex = e.get("exhibits") or {}
        if isinstance(ex, str):
            try:
                ex = json.loads(ex or "{}")
            except ValueError:
                ex = {}
        row["exhibits"].update(ex if isinstance(ex, dict) else {})
    rows = sorted(by.values(), key=lambda r: (r["date"], r["knowledge_time"] or ""), reverse=True)
    return {"rows": rows, "n": len(rows), "source": "sec.filing_events via atlas"}


def consensus_history(ticker: str, days: int = 30) -> dict:
    """Nasdaq EPS consensus revisions per report date, from /calendar/earnings/{t}/consensus-history (the vintages of
    nasdaq.earnings): {'ticker', 'next': {report_date, fiscal_quarter, latest{eps_forecast, estimates, captured_at}, first,
    revisions, captures, change{days, from, to, delta, pct}} | None, 'report_dates': [...]}; exchange-sourced, not official."""
    d = get(f"/api/v1/calendar/earnings/ticker/{ticker}/consensus-history", days=days)["data"]
    return d
