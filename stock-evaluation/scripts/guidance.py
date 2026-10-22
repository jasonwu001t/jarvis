"""Company guidance from earnings press releases (8-K item 2.02, exhibit 99.1), an official source.

For each earnings release of a ticker (atlas: sec.earnings_releases) fetch the EX-99.1 from EDGAR (cached under
<dir>/source/exhibits/), strip it to text, and parse the outlook sentences:
  next-quarter total revenue range        "We expect third quarter 2026 total revenue to be in the range of $61-64 billion."
  full-year capital expenditures range    "We anticipate 2026 capital expenditures ... in the range of $130-145 billion"
  full-year total expenses range          "We now expect full year 2026 total expenses to be in the range of $165-169 billion."
Amounts come back in USD millions with low, high and midpoint, keyed by the release date. Other issuers phrase guidance
differently: extend PATTERNS (and say so in the ticker playbook).

  python3 guidance.py --dir research/META [--since 2023-01-01] [--write]   # --write stores <dir>/guidance.json
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ATLAS = os.environ.get("ATLAS_URL", "http://127.0.0.1:8000").rstrip("/")
QUARTER_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "q1": 1, "q2": 2, "q3": 3, "q4": 4}
NUM = r"\$\s?(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*\$?\s?(\d+(?:\.\d+)?)\s*(billion|million)"
PATTERNS = {
    "revenue": re.compile(r"(first|second|third|fourth|1st|2nd|3rd|4th|q[1-4])\s+quarter\s+(?:of\s+)?(?:fiscal\s+)?(20\d\d)\s+(?:total\s+)?revenue[^.]*?" + NUM, re.I),
    "capex": re.compile(r"(?:full[- ]year\s+)?(20\d\d)\s+capital\s+expenditures?[^.]*?" + NUM, re.I),
    "expenses": re.compile(r"(?:full[- ]year\s+)?(20\d\d)\s+total\s+expenses?[^.]*?" + NUM, re.I),
}


def contact_email() -> str:
    e = os.environ.get("SEC_CONTACT_EMAIL")
    if not e:
        try:
            for line in open(os.path.expanduser("~/.config/alpharesearch/env"), encoding="utf-8"):
                if line.startswith("SEC_CONTACT_EMAIL="):
                    e = line.split("=", 1)[1].strip().strip('"')
        except OSError:
            pass
    return e or "research@example.com"


def edgar(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": f"AlphaResearch stock-evaluation {contact_email()}", "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def atlas_get(path: str, **params) -> dict:
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    with urllib.request.urlopen(urllib.request.Request(f"{ATLAS}{path}?{qs}", headers={"Accept": "application/json"}), timeout=60) as r:
        return json.load(r)


def releases(ticker: str, since: str | None = None) -> list[dict]:
    rows = atlas_get("/api/v1/data/datasets/sec.earnings_releases/rows", limit=200, **{"eq.ticker": ticker})["data"]["rows"]
    out = [{"date": r["filing_date"], "accession": r["accession_number"], "cik": str(int(r["cik"])), "url": r["primary_doc_url"]}
           for r in rows if r["form"] == "8-K" and (since is None or r["filing_date"] >= since)]
    return sorted(out, key=lambda r: r["date"])


def exhibit_text(rel: dict, cache_dir: str) -> str | None:
    os.makedirs(cache_dir, exist_ok=True)
    cache = os.path.join(cache_dir, f"{rel['accession']}-ex991.txt")
    if os.path.exists(cache):
        return open(cache, encoding="utf-8").read()
    acc_nodash = rel["accession"].replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{rel['cik']}/{acc_nodash}/"
    try:
        idx = json.loads(edgar(base + "index.json"))
    except Exception as exc:  # noqa: BLE001
        print(f"  {rel['accession']}: index fetch failed ({exc})", file=sys.stderr)
        return None
    names = [i["name"] for i in idx["directory"]["item"]]
    cands = [n for n in names if n.lower().endswith((".htm", ".html")) and re.search(r"(ex|exhibit)[-_]?99[-_.]?1|ex991|exhibit991", n.lower())]
    if not cands:
        cands = [n for n in names if n.lower().endswith((".htm", ".html")) and "99" in n.lower()]
    if not cands:
        print(f"  {rel['accession']}: no EX-99.1 among {names[:6]}", file=sys.stderr)
        return None
    time.sleep(0.4)  # SEC fair-access guidance
    raw = edgar(base + cands[0]).decode("utf-8", errors="ignore")
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    with open(cache, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


def _musd(v: str, unit: str) -> float:
    return float(v) * (1000.0 if unit.lower() == "billion" else 1.0)


def parse(text: str) -> dict:
    out = {}
    m = PATTERNS["revenue"].search(text)
    if m:
        q, y, lo, hi, unit = m.groups()
        out["revenue_next_quarter"] = {"period_key": int(y) * 10 + QUARTER_WORDS[q.lower()], "low": _musd(lo, unit), "high": _musd(hi, unit),
                                       "mid": (_musd(lo, unit) + _musd(hi, unit)) / 2, "text": m.group(0)[:200]}
    for name in ("capex", "expenses"):
        m = PATTERNS[name].search(text)
        if m:
            y, lo, hi, unit = m.groups()
            out[f"{name}_full_year"] = {"period_key": int(y) * 10, "low": _musd(lo, unit), "high": _musd(hi, unit),
                                        "mid": (_musd(lo, unit) + _musd(hi, unit)) / 2, "text": m.group(0)[:200]}
    return out


def collect(ticker: str, folder: str, since: str | None = None) -> list[dict]:
    cache_dir = os.path.join(folder, "source", "exhibits")
    out = []
    for rel in releases(ticker, since):
        text = exhibit_text(rel, cache_dir)
        g = parse(text) if text else {}
        out.append({**rel, **g, "parsed": bool(g)})
    return out


def main(argv: list[str]) -> int:
    folder = os.path.abspath(argv[argv.index("--dir") + 1]) if "--dir" in argv else os.getcwd()
    since = argv[argv.index("--since") + 1] if "--since" in argv else None
    inputs = json.load(open(os.path.join(folder, "inputs.json"), encoding="utf-8"))
    rows = collect(inputs["company"]["ticker"], folder, since)
    for r in rows:
        rv, cx = r.get("revenue_next_quarter"), r.get("capex_full_year")
        print(f"{r['date']}  rev {('Q%d %d: $%.1f-%.1fbn' % (rv['period_key'] % 10, rv['period_key'] // 10, rv['low'] / 1000, rv['high'] / 1000)) if rv else '—':<28} "
              f"capex {('FY%d: $%.0f-%.0fbn' % (cx['period_key'] // 10, cx['low'] / 1000, cx['high'] / 1000)) if cx else '—'}")
    if "--write" in argv:
        with open(os.path.join(folder, "guidance.json"), "w", encoding="utf-8") as fh:
            json.dump({"ticker": inputs["company"]["ticker"], "collected": time.strftime("%Y-%m-%d"), "releases": rows}, fh, indent=1)
        print(f"[written {os.path.join(folder, 'guidance.json')}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
