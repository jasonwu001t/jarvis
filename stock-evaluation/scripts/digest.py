"""Digest: one page across every ticker folder, regenerated after the daily monitors.

    python3 scripts/digest.py --root ~/AlphaResearch/research --out ~/AlphaResearch/research/_digest/index.html

Reads, per folder under --root that holds an inputs.json (names starting with "_" are skipped):
  inputs.json                 company name, the thesis claims (text, side, due dates), current exposure
  reports/history.jsonl       the last two records the thesis tracker appended (price, targets, exposure, rule,
                              claim statuses, EPS consensus) — the previous one is what "since the last run" means
  reports/<run date>.md       the monitor's markdown for that run: next earnings date, the EPS-consensus 30-day
                              change and the material-filings list (new filings = dates not in the previous run's md)

Renders: a summary table (one row per ticker, sorted by |upside| or by what moved), the list of what moved since
the last run across tickers, the exposure view (recommended exposure and expected-value upside per ticker, the
book's share of ten slots) and the claim due dates of the next 30 days. A folder with no history record shows as
"not run". Standard library only, Plotly via the tracker's CDN, Python 3.9 compatible; styling is imported from
thesis_tracker.py so the pages match.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from thesis_tracker import CSS, STATUS_LABEL, esc, normalise_status, pc, usd  # noqa: E402

BOOK_SLOTS = 10
TARGET_MOVE = 0.01          # house-target move that counts as "moved"
DUE_WINDOW_DAYS = 30
RE_EARNINGS = re.compile(r"^Next earnings: \*\*(\d{4}-\d{2}-\d{2})\*\*", re.M)
RE_CONSENSUS_CHANGE = re.compile(r"(\d+)-day change ([+-]?[\d.]+) \(([+-]?[\d.]+)%\)")
RE_FILING_HEAD = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\S+)(?: (.*))?$")


# ----------------------------------------------------------------------------------------------- reading
def read_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def last_records(folder: str, n: int = 2) -> list:
    p = os.path.join(folder, "reports", "history.jsonl")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        recs = [json.loads(l) for l in fh if l.strip()]
    return recs[-n:]


def parse_report_md(path: str) -> dict:
    """Earnings date, EPS-consensus change and material filings from one run's markdown report.
    `filings` is None when the report has no material-filings section (feed down that run), else the list."""
    out = {"earnings": None, "consensus_change": None, "filings": None}
    if not path or not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = RE_EARNINGS.search(text)
    if m:
        out["earnings"] = m.group(1)
    m = RE_CONSENSUS_CHANGE.search(text)
    if m:
        out["consensus_change"] = {"days": int(m.group(1)), "delta": float(m.group(2)), "pct": float(m.group(3)) / 100}
    sect = text.split("## Material filings", 1)
    if len(sect) == 2:
        out["filings"] = []
        body = sect[1].split("\n## ", 1)[0]
        for line in body.splitlines():
            if not line.startswith("- ") or line == "- none":
                continue
            # "- <date> <form> <items> · <headline>… · <url>": the monitor joins the parts with " · "; the headline is optional
            parts = [p.strip() for p in line[2:].split(" · ")]
            head = RE_FILING_HEAD.match(parts[0])
            if not head:
                continue
            date, form, items = head.group(1), head.group(2), (head.group(3) or "").strip(" —")
            url = parts[-1] if len(parts) > 1 and parts[-1].startswith("http") else ""
            headline = " · ".join(parts[1:-1] if url else parts[1:]).rstrip("…")
            out["filings"].append({"date": date, "form": form, "items": "" if items == form else items, "headline": headline, "url": url})
    return out


def _filing_key(f: dict) -> tuple:
    return (f["date"], f["url"]) if f["url"] else (f["date"], f["form"])


def report_md_for(folder: str, date: str) -> str:
    """The markdown of the run dated `date`, else the newest dated report in the folder."""
    p = os.path.join(folder, "reports", f"{date}.md") if date else ""
    if p and os.path.exists(p):
        return p
    dated = sorted(glob.glob(os.path.join(folder, "reports", "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md")))
    return dated[-1] if dated else ""


def load_folder(folder: str) -> dict:
    inp = read_json(os.path.join(folder, "inputs.json"))
    co = inp.get("company") or {}
    tk = co.get("ticker") or os.path.basename(folder)
    claims = [c for c in ((inp.get("thesis") or {}).get("claims") or []) if c.get("id")]
    recs = last_records(folder)
    now, prev = (recs[-1] if recs else None), (recs[-2] if len(recs) > 1 else None)
    md_now = parse_report_md(report_md_for(folder, now["date"]) if now else "")
    md_prev = parse_report_md(report_md_for(folder, prev["date"])) if prev else None
    return {"ticker": tk, "name": co.get("name") or tk, "folder": folder, "claims": claims, "now": now, "prev": prev,
            "md": md_now, "md_prev": md_prev, "current_exposure": (inp.get("monitor") or {}).get("current_exposure")}


def folders_under(root: str) -> list:
    out = []
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if name.startswith((".", "_")) or not os.path.isdir(p) or not os.path.exists(os.path.join(p, "inputs.json")):
            continue
        out.append(p)
    return out


# ----------------------------------------------------------------------------------------------- deriving
def claim_counts(rec: dict) -> dict:
    counts = {k: 0 for k in ("on_track", "watch", "broken", "review", "pending")}
    for st in (rec.get("claims") or {}).values():
        counts[normalise_status(st)[0]] += 1          # 'fail' recorded before the fix is broken (audit #98)
    return counts


def moves(t: dict) -> list:
    """What moved for one ticker since its previous run: (kind, text) pairs; empty for a first run or a never-run folder."""
    now, prev = t["now"], t["prev"]
    if not now or not prev:
        return []
    out = []
    if prev.get("house") and now.get("house") is not None:
        rel = now["house"] / prev["house"] - 1
        if abs(rel) > TARGET_MOVE:
            out.append(("target", f"house target {usd(prev['house'])} → <b>{usd(now['house'])}</b> ({pc(rel, 1, True)}); upside now {pc(now.get('upside'), 1, True)}"))
    if (now.get("rules") or []) != (prev.get("rules") or []):
        out.append(("rule", f"rule {esc(', '.join(prev.get('rules') or []) or 'none')} → <b>{esc(', '.join(now.get('rules') or []) or 'none')}</b>"))
    pc_, nc_ = prev.get("claims") or {}, now.get("claims") or {}
    text = {c["id"]: c.get("claim", c["id"]) for c in t["claims"]}
    for cid, st in nc_.items():
        if pc_.get(cid) not in (None, st):
            out.append(("claim", f"claim <b>{esc(cid)}</b> {STATUS_LABEL.get(pc_[cid], pc_[cid])} → <b>{STATUS_LABEL.get(st, st)}</b>"
                        + (f" <small>{esc(text[cid][:110])}</small>" if cid in text else "")))
    if t["md_prev"] is not None and t["md_prev"]["filings"] is not None and t["md"]["filings"] is not None:
        seen = {_filing_key(f) for f in t["md_prev"]["filings"]}
        for f in t["md"]["filings"]:
            if _filing_key(f) not in seen:
                link = f" <a href='{esc(f['url'])}'>filing</a>" if f["url"] else ""
                out.append(("filing", f"new filing {esc(f['date'])} {esc(f['form'])} {esc(f['items'] or '')}{(' · ' + esc(f['headline'][:100]) + '…') if f['headline'] else ''}{link}"))
    if (now.get("eps_consensus") is not None and prev.get("eps_consensus") is not None
            and now.get("eps_consensus_report_date") == prev.get("eps_consensus_report_date") and abs(now["eps_consensus"] - prev["eps_consensus"]) > 1e-9):
        rel = now["eps_consensus"] / prev["eps_consensus"] - 1 if prev["eps_consensus"] else None
        out.append(("consensus", f"EPS consensus for {esc(now['eps_consensus_report_date'])} {prev['eps_consensus']:.2f} → <b>{now['eps_consensus']:.2f}</b>"
                    + (f" ({pc(rel, 1, True)})" if rel is not None else "")))
    return out


def due_claims(tickers: list, today: dt.date) -> list:
    """Claims with a due date inside the next DUE_WINDOW_DAYS across tickers, soonest first."""
    end = today + dt.timedelta(days=DUE_WINDOW_DAYS)
    out = []
    for t in tickers:
        statuses = (t["now"] or {}).get("claims") or {}
        for c in t["claims"]:
            try:
                due = dt.date.fromisoformat(str(c.get("due") or ""))
            except ValueError:
                continue
            if today <= due <= end:
                out.append({"ticker": t["ticker"], "due": due, "claim": c.get("claim", c["id"]), "id": c["id"],
                            "side": c.get("side", "buy"), "status": statuses.get(c["id"], c.get("status") or "pending")})
    return sorted(out, key=lambda d: (d["due"], d["ticker"]))


def _d(x, y):
    return None if x is None or y is None else x - y


def row(t: dict) -> dict:
    """Everything the summary table shows for one ticker, numbers unformatted."""
    now, prev, md = t["now"], t["prev"], t["md"]
    if not now:
        return {"ticker": t["ticker"], "name": t["name"], "run": False, "moves": []}
    ev = (now["expected"] / now["price"] - 1) if now.get("expected") and now.get("price") else None
    return {"ticker": t["ticker"], "name": t["name"], "run": True, "date": now["date"], "price": now["price"], "house": now["house"],
            "upside": now.get("upside"), "ev_upside": ev, "rule": ", ".join(now.get("rules") or []), "exposure": now.get("exposure"),
            "bear": now.get("bear"), "base": now.get("base"), "bull": now.get("bull"),
            "d_price": _d(now["price"], prev["price"]) / prev["price"] if prev and prev.get("price") else None,
            "d_house": _d(now["house"], prev["house"]) / prev["house"] if prev and prev.get("house") else None,
            "claims": claim_counts(now), "filing_date": max((f["date"] for f in (md["filings"] or [])), default=None),
            "eps_consensus": now.get("eps_consensus"), "consensus_change": md["consensus_change"], "earnings": md["earnings"],
            "moves": moves(t)}


# ----------------------------------------------------------------------------------------------- page
def rel(root: str, out_path: str, folder: str, name: str) -> str:
    return os.path.relpath(os.path.join(folder, "reports", name), os.path.dirname(os.path.abspath(out_path))).replace(os.sep, "/")


def _sgn(x, cls=True, d=1):
    if x is None:
        return "—"
    c = "good" if x > 0 else ("bad" if x < 0 else "")
    return f"<span class='{c}'>{pc(x, d, True)}</span>" if cls else pc(x, d, True)


def _claims_cell(c: dict) -> str:
    parts = [(k, c[k]) for k in ("on_track", "watch", "broken", "review") if c.get(k)]
    if not parts:
        return "<small>no claims</small>" if not c.get("pending") else f"<small>{c['pending']} pending</small>"
    return " ".join(f"<span class='pill {k}' title='{STATUS_LABEL[k]}'>{n}</span>" for k, n in parts) + (f" <small>{c['pending']} pending</small>" if c.get("pending") else "")


def table_rows(rows: list, root: str, out_path: str, by: dict) -> str:
    H = []
    for r in rows:
        t = by[r["ticker"]]
        links = f"<a href='{rel(root, out_path, t['folder'], 'latest.html')}'>report</a> · <a href='{rel(root, out_path, t['folder'], 'thesis.html')}'>thesis</a>"
        if not r["run"]:
            H.append(f"<tr class='notrun'><td class='l'><b>{esc(r['ticker'])}</b><br><small>{esc(r['name'])}</small></td>"
                     f"<td class='l' colspan='12'><span class='pill pending'>not run</span> <small>no reports/history.jsonl record; run the monitor</small></td><td class='d'>{links}</td></tr>")
            continue
        cc = r["consensus_change"]
        cons = (f"{r['eps_consensus']:.2f}" if r["eps_consensus"] is not None else "—") + (f"<br><small>{_sgn(cc['pct'])} {cc['days']}d</small>" if cc else "")
        cls = " class='moved'" if r["moves"] else ""
        H.append(
            f"<tr{cls}><td class='l'><b>{esc(r['ticker'])}</b><br><small>{esc(r['name'])}</small></td>"
            f"<td class='num'>{usd(r['price'], 2)}<br><small>{_sgn(r['d_price'])}</small></td>"
            f"<td class='num'><b>{usd(r['house'])}</b><br><small>{_sgn(r['d_house'])}</small></td>"
            f"<td class='num'><b>{_sgn(r['upside'])}</b></td>"
            f"<td class='l'>{esc(r['rule']) or '—'}</td>"
            f"<td class='num'>{pc(r['exposure'], 0) if r['exposure'] is not None else '—'}</td>"
            f"<td class='num'>{usd(r['bear'])} · {usd(r['base'])} · {usd(r['bull'])}</td>"
            f"<td class='d'>{_claims_cell(r['claims'])}</td>"
            f"<td class='d'>{esc(r['filing_date'] or '—')}</td>"
            f"<td class='num'>{cons}</td>"
            f"<td class='d'>{esc(r['earnings'] or '—')}</td>"
            f"<td class='d'><small>{esc(r['date'])}</small></td>"
            f"<td class='d'>{links}</td></tr>")
    return "".join(H)


def page(rows: list, by: dict, root: str, out_path: str, today: dt.date, sort: str, now: dt.datetime) -> str:
    run = [r for r in rows if r["run"]]
    moved = [(r["ticker"], kind, txt) for r in rows for kind, txt in r["moves"]]
    first_run = [r["ticker"] for r in run if by[r["ticker"]]["prev"] is None]
    due = due_claims(list(by.values()), today)
    exposures = [r["exposure"] for r in run if r["exposure"] is not None]
    book = sum(exposures) / BOOK_SLOTS if exposures else None
    stale = [r["ticker"] for r in run if r["date"] != today.isoformat()]

    moved_html = "".join(f"<li><b>{esc(tk)}</b> · {txt}</li>" for tk, kind, txt in moved) or "<li>nothing moved beyond the thresholds since the previous runs</li>"
    if first_run:
        moved_html += f"<li><small>first run, no previous record to compare: {esc(', '.join(first_run))}</small></li>"
    due_html = "".join(
        f"<li><b>{esc(d['due'].isoformat())}</b> · <b>{esc(d['ticker'])}</b> · {esc(d['claim'])} "
        f"<span class='pill {d['status']}'>{STATUS_LABEL.get(d['status'], d['status'])}</span> <small>{'risk' if d['side'] != 'buy' else 'buy-side'}</small></li>"
        for d in due) or f"<li>no claim due in the next {DUE_WINDOW_DAYS} days</li>"

    ex_rows = sorted(run, key=lambda r: -(r["exposure"] or 0))
    payload = json.dumps({"tickers": [r["ticker"] for r in ex_rows], "exposure": [r["exposure"] for r in ex_rows],
                          "ev": [r["ev_upside"] for r in ex_rows], "upside": [r["upside"] for r in ex_rows]})
    sort_note = {"upside": "sorted by |upside to the house target|", "moved": "sorted by what moved since the last run, then |upside|"}[sort]
    folders_read = ", ".join(os.path.basename(by[r["ticker"]]["folder"]) for r in rows)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Research digest {today.isoformat()}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>{CSS}
tr.moved td:first-child{{box-shadow:inset 3px 0 0 var(--s1)}} tr.notrun td{{color:var(--muted)}} td.d{{text-align:left;white-space:nowrap}}
</style></head><body>
<nav><a href="#table">Tickers</a><a href="#moved">What moved</a><a href="#exposure">Exposure</a><a href="#due">Due</a></nav>
<main>
<h1>Research digest — {today.isoformat()}</h1>
<p class="sub">{len(run)} of {len(rows)} folders run · {len(moved)} move{'s' if len(moved) != 1 else ''} since the previous runs · {len(due)} claim{'s' if len(due) != 1 else ''} due in {DUE_WINDOW_DAYS} days
{(' · <b class="warn">not run today: ' + esc(', '.join(stale)) + '</b>') if stale else ''}</p>
<div class="tiles">
<div class="tile"><div class="k">Book: recommended exposure</div><div class="v">{pc(book, 0) if book is not None else '—'}</div><div class="n">sum of {len(exposures)} exposures over {BOOK_SLOTS} slots ({sum(exposures):.2f} slots)</div></div>
<div class="tile"><div class="k">Add zone (upside ≥ 20%)</div><div class="v">{sum(1 for r in run if (r['upside'] or 0) >= 0.2)}</div><div class="n">{esc(', '.join(r['ticker'] for r in run if (r['upside'] or 0) >= 0.2)) or 'none'}</div></div>
<div class="tile"><div class="k">Stretched (price &gt; 10% over house)</div><div class="v">{sum(1 for r in run if (r['upside'] or 0) <= -0.1)}</div><div class="n">{esc(', '.join(r['ticker'] for r in run if (r['upside'] or 0) <= -0.1)) or 'none'}</div></div>
<div class="tile"><div class="k">Broken claims</div><div class="v">{sum(r['claims']['broken'] for r in run)}</div><div class="n">{sum(r['claims']['watch'] for r in run)} on watch · {sum(r['claims']['review'] for r in run)} to review</div></div>
</div>
<h2 id="table">Tickers</h2>
<p class="sub">{sort_note}; day changes are against each folder's previous run. Claims: <span class="pill on_track">on track</span> <span class="pill watch">watch</span> <span class="pill broken">broken</span> <span class="pill review">review</span>. EPS consensus is Nasdaq's for the next print (exchange-published third-party data) with its change over the window the monitor reports.</p>
<div class="tbl"><table><thead><tr><th>Ticker</th><th>Price<br><small>day</small></th><th>House<br><small>day</small></th><th>Upside</th><th>Rule</th><th>Exposure</th><th>Bear · Base · Bull</th><th>Claims</th><th>Newest filing</th><th>EPS cons.</th><th>Next earnings</th><th>Run</th><th>Pages</th></tr></thead>
<tbody>{table_rows(rows, root, out_path, by)}</tbody></table></div>
<h2 id="moved">What moved since the last run</h2>
<p class="sub">House-target moves beyond {pc(TARGET_MOVE, 0)}, rule changes, claim status changes, filings new to the material-filings list, and EPS-consensus moves for the same report date, from each folder's last two history records and reports.</p>
<ul>{moved_html}</ul>
<h2 id="exposure">Exposure</h2>
<p class="sub">Recommended exposure after the overlays (bars) and the expected-value upside, probability-weighted target against price (markers). The book line is the sum of exposures as a share of a {BOOK_SLOTS}-slot book: <b>{pc(book, 0) if book is not None else '—'}</b>.</p>
<div id="c_exposure" class="chart"></div>
<h2 id="due">Due in the next {DUE_WINDOW_DAYS} days</h2>
<ul>{due_html}</ul>
<footer>Not investment advice. Generated {now.strftime('%Y-%m-%d %H:%M')} by the stock-evaluation skill (scripts/digest.py) from {esc(root)}: {esc(folders_read)}.</footer>
</main>
<script>
const D={payload};
const dark=matchMedia('(prefers-color-scheme: dark)').matches;
const C={{s1:dark?'#3987e5':'#2a78d6',s2:dark?'#d95926':'#eb6834',text:dark?'#f0efec':'#0b0b0b',t2:dark?'#c3c2b7':'#52514e',grid:dark?'#3a3936':'#e6e4de'}};
Plotly.newPlot('c_exposure',[
 {{type:'bar',x:D.tickers,y:D.exposure,name:'recommended exposure',marker:{{color:C.s1}},hovertemplate:'%{{x}}<br>exposure %{{y:.0%}}<extra></extra>'}},
 {{type:'scatter',mode:'markers',x:D.tickers,y:D.ev,yaxis:'y2',name:'expected-value upside',marker:{{color:C.s2,size:11,symbol:'diamond'}},hovertemplate:'%{{x}}<br>EV upside %{{y:+.1%}}<extra></extra>'}}],
 {{paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{{color:C.t2,size:12}},margin:{{l:60,r:70,t:36,b:48}},
  title:{{text:'Recommended exposure per ticker and expected-value upside',font:{{size:14,color:C.text}},x:0}},legend:{{orientation:'h',y:-0.18}},
  yaxis:{{title:'exposure',tickformat:'.0%',gridcolor:C.grid,zeroline:false,range:[0,Math.max(1,...D.exposure.filter(v=>v!=null))*1.05]}},
  yaxis2:{{title:'EV upside',tickformat:'+.0%',overlaying:'y',side:'right',showgrid:false,zeroline:true,zerolinecolor:C.grid}},
  xaxis:{{showgrid:false}}}},{{displayModeBar:false,responsive:true}});
</script></body></html>"""


# ----------------------------------------------------------------------------------------------- entry
def build(root: str, out_path: str, today: dt.date = None, sort: str = "upside", now: dt.datetime = None) -> str:
    today = today or dt.date.today()
    now = now or dt.datetime.now()
    tickers = [load_folder(f) for f in folders_under(root)]
    by = {t["ticker"]: t for t in tickers}
    rows = [row(t) for t in tickers]
    key = (lambda r: (-len(r["moves"]), -abs(r.get("upside") or 0))) if sort == "moved" else (lambda r: -abs(r.get("upside") or 0))
    rows = sorted([r for r in rows if r["run"]], key=key) + [r for r in rows if not r["run"]]
    return page(rows, by, root, out_path, today, sort, now)


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="One page across every research folder: table, what moved, exposure, due claims.")
    ap.add_argument("--root", default=os.path.expanduser("~/AlphaResearch/research"))
    ap.add_argument("--out", default=None, help="default <root>/_digest/index.html")
    ap.add_argument("--sort", choices=("upside", "moved"), default="upside")
    a = ap.parse_args(argv)
    root = os.path.abspath(os.path.expanduser(a.root))
    out = os.path.abspath(os.path.expanduser(a.out or os.path.join(root, "_digest", "index.html")))
    html = build(root, out, sort=a.sort)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
