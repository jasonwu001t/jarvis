"""The guidance street fill_from_atlas.py builds, and what feeds it, from the 2026-10-26 bug audit (#89, #95, #93,
#190, #142, #99), each on synthetic data. Run with `python3 -B -m unittest discover -s scripts/tests` from the skill
root."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _synth  # noqa: E402
import atlas_data  # noqa: E402
import backtest  # noqa: E402
import guidance  # noqa: E402
import monitor  # noqa: E402
import report_html  # noqa: E402
import valuation_engine as mm  # noqa: E402
from test_onboarding_faults import FillCase  # noqa: E402


def _lines(inp):
    return {line: {int(k): v for k, v in vals.items()} for line, vals in inp["lines"].items()}


def _warned(inp, *words):
    return [n for n in inp["_sources"]["notes"] if n.startswith("WARNING") and all(w in n for w in words)]


def _backtest_data(world, guidance_rows=()):
    """backtest.fetch_all's shape from an AtlasWorld: KPI rows, no balance extras on the one decision day (2026-07-30),
    one price, one 10-year yield."""
    K = {kpi: [{"key": k, "end": v["end"], "value": v["value"], "kind": "annual" if k % 10 == 0 else "quarterly"}
               for k, v in sorted(series.items())] for kpi, series in world.kpis.items()}
    return {"kpis": K, "extras": {"2026-07-30": {}}, "rf": {"2026-07-01": 0.04},
            "prices": {"ZZZ": {"2026-07-30": 100.0}, "SPY": {"2026-07-30": 500.0}}, "guidance": list(guidance_rows)}


class TtmOverSharedQuarters(FillCase):
    """#89: a quarter atlas does not serve for one line counted as zero against four quarters of revenue (CRWD: D&A in
    one quarter of four gave da_ratio 0.48%, a quarter of the true ratio)."""

    def test_a_missing_quarter_is_left_out_of_both_sides(self):
        world = _synth.AtlasWorld(latest=(2026, 2))
        for k in (20253, 20254, 20261):          # D&A in the latest quarter only; Q4 not derivable without Q3
            del world.kpis["depreciation_amortization"][k]
        del world.kpis["operating_income"][20253]
        inp = self.fill(world)
        st = inp["_street"]
        self.assertAlmostEqual(st["da_ratio"], 0.05, places=9)
        self.assertAlmostEqual(st["margin_ttm"], 0.30, places=9)
        self.assertAlmostEqual(st["wc_ratio"], 0.02, places=9)     # not derived for a quarter without D&A
        self.assertTrue(_warned(inp, "d_and_a"))
        self.assertTrue(_warned(inp, "operating_income"))

    def test_a_missing_q4_is_the_fiscal_year_less_q1_q3(self):
        world = _synth.AtlasWorld(latest=(2026, 2))
        oi = world.kpis["operating_income"].pop(20254)["value"]
        da = world.kpis["depreciation_amortization"].pop(20254)["value"]
        inp = self.fill(world)
        L = _lines(inp)
        self.assertAlmostEqual(L["operating_income"][20254], oi, places=6)
        self.assertAlmostEqual(L["d_and_a"][20254], da, places=6)
        self.assertAlmostEqual(inp["_street"]["margin_ttm"], 0.30, places=9)
        self.assertAlmostEqual(inp["_street"]["da_ratio"], 0.05, places=9)
        self.assertFalse(_warned(inp, "operating_income"))

    def test_the_backtest_street_uses_the_same_rule(self):
        world = _synth.AtlasWorld(latest=(2026, 2))
        for k in (20253, 20254, 20261):
            del world.kpis["depreciation_amortization"][k]
        del world.kpis["operating_income"][20253]
        inp = backtest.build_inputs(_synth.engine_inputs(), _backtest_data(world), 20262, "2026-07-30", "momentum")
        L = inp["lines"]
        self.assertAlmostEqual(L["d_and_a"]["20263"] / L["revenue"]["20263"], 0.05, places=9)
        self.assertAlmostEqual(inp["_street"]["margin_ttm"], 0.30, places=9)
        self.assertEqual(inp["_street"]["ttm_gaps"]["d_and_a / revenue"], [20262])


if __name__ == "__main__":
    unittest.main()
