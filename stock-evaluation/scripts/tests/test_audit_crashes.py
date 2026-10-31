"""Crashes the 2026-10-26 bug audit found in the skill (#23, #90, #94, ...), each on synthetic data. Run with
`python3 -B -m unittest discover -s scripts/tests` from the skill root."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _synth  # noqa: E402
import backtest  # noqa: E402
import fill_from_atlas  # noqa: E402
import monitor  # noqa: E402
import new_ticker  # noqa: E402
import report_html  # noqa: E402
import valuation_engine as mm  # noqa: E402
from test_onboarding_faults import FillCase  # noqa: E402


class BacktestSkipsDateLabelledPoints(unittest.TestCase):
    """#23: atlas serves shares_outstanding_cover as date-labelled 'instant' points; period_key raised ValueError and
    every backtest aborted."""

    def test_fetch_all_reads_past_an_instant_point(self):
        kpis = [{"id": "revenue", "quarterly": [{"period": "2026-Q2", "kind": "quarterly", "end": "2026-06-30",
                                                 "value": 5e9, "filed": "2026-07-30"}],
                 "annual": [{"period": "FY2025", "kind": "annual", "end": "2025-12-31", "value": 18e9}]},
                {"id": "shares_outstanding_cover", "quarterly": [{"period": "2026-07-22", "kind": "instant",
                                                                  "end": "2026-07-22", "value": 1e9}], "annual": []}]

        def get(path, **params):
            if path.startswith("/api/v1/filings/"):
                return {"data": {"xbrl": {"kpis": kpis}}}
            return {"data": {"rows": []}}

        saved = backtest.get, backtest.guid.collect
        backtest.get, backtest.guid.collect = get, lambda *a, **kw: []
        try:
            out = backtest.fetch_all("ZZZ", "/nonexistent", "2025-01-01")
        finally:
            backtest.get, backtest.guid.collect = saved
        self.assertEqual([r["key"] for r in out["kpis"]["revenue"]], [20262, 20250])
        self.assertEqual(out["kpis"]["shares_outstanding_cover"], [])


class RevenueOnlySegments(FillCase):
    """#90: a member with revenue and no operating income (oi_line None) made ttm('segoi:<name>') raise KeyError and
    the fill wrote no inputs.json."""

    def test_the_fill_keeps_a_revenue_only_segment(self):
        world = _synth.AtlasWorld(latest=(2026, 2))
        rev = {y * 10 + i: world.quarter_rev(y, i) * 0.4 for y, i in world.quarters()}
        segs = {"defs": {"Alpha": {"parent": None, "oi_line": None}}, "lines": {"seg:Alpha": rev},
                "source": "sec.segment_facts via atlas", "members_all": ["Alpha"]}
        fill = FillCase.fill.__get__(self)

        def with_segments(w, *args):
            original = fill_from_atlas.atlas_data.segments
            saved_fill = fill_from_atlas.main

            def main(argv):
                fill_from_atlas.atlas_data.segments = lambda ticker, **kw: segs
                return saved_fill(argv)
            fill_from_atlas.main = main
            try:
                return fill(w, *args)
            finally:
                fill_from_atlas.main = saved_fill
                fill_from_atlas.atlas_data.segments = original

        inp = with_segments(world)
        self.assertEqual(inp["segments"], {"Alpha": {"parent": None, "oi_line": None}})
        self.assertNotIn("segoi:Alpha", inp["lines"])
        self.assertTrue(any(int(k) % 10 for k in inp["lines"]["seg:Alpha"]))


class ReportWithoutTheOwnRange(unittest.TestCase):
    """#94: new_ticker scaffolds reference_multiples pe5y_* as null and fill_from_atlas never sets them; the report
    raised TypeError after the markdown was written."""

    def test_the_report_renders_with_null_reference_multiples(self):
        inp = _synth.engine_inputs()
        inp["reference_multiples"].update(pe5y_low=None, pe5y_avg=None, pe5y_high=None)
        page = report_html.render(inp, mm.Model(inp).run(), {}, [], {}, [], [], None)
        self.assertIn("no own five-year forward range on record", page)
        self.assertIn("5y range not on record", page)


class ShortHorizon(unittest.TestCase):
    """#144: with no transition years and consensus only to FY+2, FY+4 revenue does not exist, revenue_cagr_5y is None
    and the engine summary and the monitor markdown raised TypeError. #252: the report's generic narrative indexed
    years_ext[-1] (IndexError)."""

    def inputs(self):
        inp = _synth.engine_inputs()
        inp["blend"]["convergence_years"] = 0
        return inp

    def test_summary_markdown_and_report_render_without_a_five_year_cagr(self):
        inp = self.inputs()
        out = mm.Model(inp).run()
        self.assertIsNone(out["scenarios"]["base"]["revenue_cagr_5y"])
        self.assertIn("base", mm.summary(out))
        md = monitor.render(inp, out, {}, [], {}, [])
        self.assertIn("revenue CAGR", md)
        page = report_html.render(inp, out, {}, [], {}, [], [], None)
        self.assertIn("2. Two periods", page)


class ShortPriceHistory(unittest.TestCase):
    """#258: with fewer than 61 or 200 closes the overlay state holds None, and the monitor formatted it unguarded
    (TypeError) or printed 'below the 200-day' with no SMA."""

    def test_position_block_with_no_vol_and_no_sma(self):
        inp = _synth.engine_inputs()
        out = mm.Model(inp).run()
        state = {"nfci": None, "nfci_date": None, "vix": None, "baa10y": None, "stress": [], "regime_cap": 1.0,
                 "realized_vol": None, "vol_scale": 1.0, "above_sma": None, "sma": None}
        result = {"staged": False, "recommended": 0.5, "signal": 0.5, "after_regime": 0.5, "after_vol": 0.5}
        live = {"position": {"state": state, "result": result, "rule_exposure": 0.5, "source": "test", "current": None}}
        md = monitor.render(inp, out, live, [], {}, [])
        self.assertIn("n/a (fewer than 200 closes)", md)
        self.assertIn("too little history", md)
        self.assertNotIn("below the 200-day", md)
        page = report_html.render(inp, out, live, [], {}, [], [], None)
        self.assertIn("n/a (fewer than 200 closes)", page)


class NewTickerArguments(unittest.TestCase):
    """#192: a flag placed first had its value taken as the ticker."""

    def test_flags_in_any_position(self):
        tmp = tempfile.mkdtemp()
        try:
            folder = os.path.join(tmp, "x")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(new_ticker.main(["--dir", folder, "--fye", "9", "nvda", "NVIDIA Corporation"]), 0)
            inp = json.load(open(os.path.join(folder, "inputs.json"), encoding="utf-8"))
            self.assertEqual(inp["company"]["ticker"], "NVDA")
            self.assertEqual(inp["company"]["fiscal_year_end_month"], 9)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(new_ticker.main(["NVDA", "N", "--fye", "x"]), 2)
        finally:
            shutil.rmtree(tmp)


class BacktestLag(unittest.TestCase):
    """#253: --lag 0 read after[-1], so every decision fell on the last price date."""

    def test_a_lag_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            backtest.release_evals("ZZZ", {"kpis": {"revenue": []}, "prices": {"ZZZ": {}}}, "2025-01-01", lag_days=0)


if __name__ == "__main__":
    unittest.main()
