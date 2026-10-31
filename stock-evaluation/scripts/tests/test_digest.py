"""digest.py on two synthetic folders: ACME has two history records, a claims board and two daily reports; NEVR was
scaffolded but never run. Run with `python3 -m unittest scripts/tests/test_digest.py` (or pytest) from the skill root."""
import datetime as dt
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import digest  # noqa: E402

TODAY = dt.date(2026, 10, 25)


def _inputs(ticker, name, claims):
    return {"company": {"ticker": ticker, "name": name, "currency": "USD", "fiscal_year_end_month": 12},
            "as_of": {"latest_reported_fy": 2026, "latest_reported_q": 2, "balance_sheet_date": "2026-06-30", "consensus_date": "2026-08-01"},
            "monitor": {"rules": [], "position_source": "expected_value", "current_exposure": None},
            "thesis": {"summary": "test", "claims": claims}}


def _record(date, price, house, exposure, rules, claims, eps=None):
    return {"date": date, "price": price, "price_date": date, "risk_free": 0.05, "beta": 1.2, "wacc": 0.1, "rf_date": date,
            "rf_source": "treasury.yield_curve", "beta_to": date, "bear": house * 0.7, "base": house, "bull": house * 1.3,
            "house": house, "upside": house / price - 1, "expected": house * 0.95, "exposure": exposure, "rules": rules,
            "latest_key": 20262, "consensus_date": "2026-08-01", "claims": claims,
            "eps_consensus": eps, "eps_consensus_report_date": "2026-11-03" if eps is not None else None}


REPORT_PREV = """# ACME valuation monitor — 2026-10-24

Price $100.00 (2026-10-23) · latest reported quarter FY2026 Q2 (balance sheet 2026-06-30) · consensus block dated 2026-08-01
Next earnings: **2026-11-03** (after_hours, 2026-09), Nasdaq EPS consensus 1.60
EPS consensus history (2026-11-03, exchange source): 1.60 on 10 estimates; 2 revision(s) over 9 captures since 2026-10-01; 30-day change -0.02 (-1.2%)

## Material filings (8-K items 1.01, 1.02, 2.01, 2.03, 2.05, 2.06, 3.02, 5.02, 8.01; 6-Ks) since 2026-06-26

- 2026-09-01 8-K 5.02, 9.01 · https://www.sec.gov/Archives/edgar/data/1/000000000126000001/acme-20260901.htm

## Live inputs

- Risk-free 5.00%
"""

REPORT_NOW = """# ACME valuation monitor — 2026-10-25

Price $104.00 (2026-10-24) · latest reported quarter FY2026 Q2 (balance sheet 2026-06-30) · consensus block dated 2026-08-01
Next earnings: **2026-11-03** (after_hours, 2026-09), Nasdaq EPS consensus 1.68
EPS consensus history (2026-11-03, exchange source): 1.68 on 11 estimates; 3 revision(s) over 10 captures since 2026-10-01; 30-day change +0.04 (+2.4%)

## Material filings (8-K items 1.01, 1.02, 2.01, 2.03, 2.05, 2.06, 3.02, 5.02, 8.01; 6-Ks) since 2026-06-27

- 2026-10-24 8-K 1.01, 2.03 · On October 24, 2026, ACME entered into a credit agreement… · https://www.sec.gov/Archives/edgar/data/1/000000000126000002/acme-20261024.htm
- 2026-09-01 8-K 5.02 · Director retirement… · https://www.sec.gov/Archives/edgar/data/1/000000000126000001/acme-20260901.htm

## Live inputs

- Risk-free 5.00%
"""


class DigestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="digest-test-")
        acme = os.path.join(cls.root, "ACME")
        os.makedirs(os.path.join(acme, "reports"))
        claims = [
            {"id": "growth", "side": "buy", "weight": "strong", "claim": "Revenue grows 20%+", "check": {"kind": "yoy", "line": "revenue", "min": 0.2}},
            {"id": "ramp", "side": "buy", "weight": "strong", "claim": "The new product ships in Q4", "status": "pending", "as_of": "2026-10-01", "due": "2026-11-05"},
            {"id": "far", "side": "sell", "weight": "weak", "claim": "A risk due far out", "status": "watch", "as_of": "2026-10-01", "due": "2027-02-10"},
            {"id": "price", "side": "sell", "weight": "strong", "claim": "The price runs ahead of the house value", "check": {"kind": "rule", "name": "Stretched"}},
        ]
        with open(os.path.join(acme, "inputs.json"), "w") as fh:
            json.dump(_inputs("ACME", "Acme Corp", claims), fh)
        recs = [_record("2026-10-24", 100.0, 120.0, 0.5, ["Add zone"], {"growth": "on_track", "ramp": "pending", "far": "watch", "price": "on_track"}, eps=1.60),
                _record("2026-10-25", 104.0, 126.0, 0.6, ["Hold zone"], {"growth": "watch", "ramp": "pending", "far": "watch", "price": "on_track"}, eps=1.68)]
        with open(os.path.join(acme, "reports", "history.jsonl"), "w") as fh:
            for r in recs:
                fh.write(json.dumps(r) + "\n")
        for name, text in (("2026-10-24.md", REPORT_PREV), ("2026-10-25.md", REPORT_NOW)):
            with open(os.path.join(acme, "reports", name), "w") as fh:
                fh.write(text)
        nevr = os.path.join(cls.root, "NEVR")
        os.makedirs(nevr)
        with open(os.path.join(nevr, "inputs.json"), "w") as fh:
            json.dump(_inputs("NEVR", "Never Run Inc.", []), fh)
        os.makedirs(os.path.join(cls.root, "_digest"))     # skipped: underscore folders are not tickers
        cls.out = os.path.join(cls.root, "_digest", "index.html")
        cls.html = digest.build(cls.root, cls.out, today=TODAY, now=dt.datetime(2026, 10, 25, 7, 10))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def test_table_rows(self):
        h = self.html
        self.assertIn("<b>ACME</b>", h)
        self.assertIn("$104.00", h)                       # price
        self.assertIn("<b>$126</b>", h)                   # house target
        self.assertIn("+21.2%", h)                        # upside 126/104-1
        self.assertIn("+4.0%", h)                         # day change of price
        self.assertIn("+5.0%", h)                         # day change of the house target
        self.assertIn("Hold zone", h)                     # rule in force
        self.assertIn("60%", h)                           # recommended exposure
        self.assertIn("$88 · $126 · $164", h)             # bear · base · bull
        self.assertIn("2026-10-24", h)                    # newest filing date
        self.assertIn("1.68", h)                          # EPS consensus
        self.assertIn("+2.4%</span> 30d", h)              # its 30-day change
        self.assertIn("2026-11-03", h)                    # next earnings
        self.assertIn("href='../ACME/reports/latest.html'", h)
        self.assertIn("href='../ACME/reports/thesis.html'", h)
        # claims: 2 on track (growth→watch leaves far=watch, growth=watch; on_track: price), so 1 on track, 2 watch, 1 pending
        self.assertIn("<span class='pill on_track' title='On track'>1</span> <span class='pill watch' title='Watch'>2</span>", h)
        self.assertIn("1 pending", h)
        # the never-run folder
        self.assertIn("<b>NEVR</b>", h)
        self.assertIn(">not run</span>", h)
        self.assertIn("href='../NEVR/reports/thesis.html'", h)
        self.assertIn("1 of 2 folders run", h)
        # book: one exposure of 0.6 over ten slots
        self.assertIn("<div class=\"v\">6%</div>", h)

    def test_moved_list(self):
        h = self.html.split('id="moved"')[1].split('id="exposure"')[0]
        self.assertIn("house target $120 → <b>$126</b> (+5.0%)", h)
        self.assertIn("rule Add zone → <b>Hold zone</b>", h)
        self.assertIn("claim <b>growth</b> On track → <b>Watch</b>", h)
        self.assertIn("new filing 2026-10-24 8-K 1.01, 2.03", h)
        self.assertNotIn("new filing 2026-09-01", h)       # same accession, items re-formatted: not new
        self.assertIn("EPS consensus for 2026-11-03 1.60 → <b>1.68</b> (+5.0%)", h)
        self.assertNotIn("NEVR", h)

    def test_due_list(self):
        h = self.html.split('id="due"')[1].split("<footer>")[0]
        self.assertIn("<b>2026-11-05</b> · <b>ACME</b> · The new product ships in Q4", h)
        self.assertNotIn("2027-02-10", h)                   # outside the 30-day window

    def test_footer_and_styling(self):
        self.assertIn("Generated 2026-10-25 07:10", self.html)
        self.assertIn("ACME, NEVR", self.html)
        self.assertIn("cdn.plot.ly/plotly-2.35.2.min.js", self.html)
        self.assertIn("prefers-color-scheme:dark", self.html)

    def test_parse_report_md_without_filings_section(self):
        p = os.path.join(self.root, "nofilings.md")
        with open(p, "w") as fh:
            fh.write("# X\n\nNext earnings: **2026-12-01** (x, y), Nasdaq EPS consensus 1\n")
        md = digest.parse_report_md(p)
        self.assertEqual(md["earnings"], "2026-12-01")
        self.assertIsNone(md["filings"])


if __name__ == "__main__":
    unittest.main()
