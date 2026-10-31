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


class OtherIncomeWithAnInterestExpenseGap(FillCase):
    """#95: one missing quarter of interest expense dropped the debt cost from the forecast other income, silently."""

    def world(self):
        return _synth.AtlasWorld(latest=(2026, 2), cash=4000.0, debt=1000.0, interest_income=40.0, interest_expense=10.0)

    def test_the_quarters_present_are_annualised_and_said_so(self):
        world = self.world()
        del world.kpis["interest_expense"][20261]
        inp = self.fill(world)
        oth = inp["_street"]["other_income"]
        self.assertAlmostEqual(oth["annual"], 0.04 * 4000.0 - 0.04 * 1000.0, places=6)   # 30 over three quarters = 40 a year
        self.assertLess(oth["annual"], oth["interest_income_ttm"])
        self.assertTrue(_warned(inp, "forecast other income", "interest expense"))

    def test_a_missing_q4_is_derived_from_the_year(self):
        world = self.world()
        del world.kpis["interest_expense"][20254]
        inp = self.fill(world)
        oth = inp["_street"]["other_income"]
        self.assertAlmostEqual(oth["interest_expense_ttm"], 40.0, places=6)
        self.assertAlmostEqual(oth["annual"], 120.0, places=6)
        self.assertFalse(_warned(inp, "forecast other income"))

    def test_no_interest_expense_with_debt_carries_the_non_operating_line(self):
        world = self.world()
        for k in (20253, 20254, 20261, 20262):
            del world.kpis["interest_expense"][k]
        inp = self.fill(world)
        oth = inp["_street"]["other_income"]
        self.assertAlmostEqual(oth["annual"], 4 * (40.0 - 10.0), places=6)     # pretax − operating income nets the debt cost
        self.assertIn("non-operating", oth["source"])
        self.assertTrue(_warned(inp, "forecast other income"))


class GuidanceBasis(FillCase):
    """#93: a non-GAAP operating-income guide was beat-adjusted against GAAP actuals and set the guided quarter's GAAP
    operating income (CRWD: oi_beat −0.342); with GAAP and non-GAAP rows the first row won."""

    def rows_payload(self, rows):
        cols = ["accession_number", "knowledge_time", "period_key", "fiscal_year", "fiscal_quarter", "metric", "period_kind",
                "low", "high", "mid", "unit", "basis", "source_text"]
        return {"data": {"columns": [{"name": c} for c in cols], "rows": [[r.get(c) for c in cols] for r in rows]}}

    def test_gaap_row_wins_in_either_order(self):
        base = {"accession_number": "a1", "knowledge_time": "2026-07-29T13:00:00", "period_key": 20263,
                "metric": "operating_income", "period_kind": "next_quarter", "unit": "USD", "source_text": "x"}
        gaap = {**base, "low": 90e6, "high": 110e6, "mid": 100e6, "basis": "gaap"}
        non = {**base, "low": 490e6, "high": 510e6, "mid": 500e6, "basis": "non_gaap"}
        saved = atlas_data.get
        try:
            for rows in ([gaap, non], [non, gaap]):
                atlas_data.get = lambda path, _rows=rows, **kw: self.rows_payload(_rows)
                oi = atlas_data.guidance_releases("ZZZ")[0]["operating_income_next_quarter"]
                self.assertEqual((oi["mid"], oi["basis"]), (100.0, "gaap"))
            atlas_data.get = lambda path, **kw: self.rows_payload([non])
            self.assertEqual(atlas_data.guidance_releases("ZZZ")[0]["operating_income_next_quarter"]["basis"], "non_gaap")
        finally:
            atlas_data.get = saved

    def releases(self, world, basis):
        rev = lambda k: world.kpis["revenue"][k]["value"]
        out = []
        for k, date in ((20261, "2026-02-01"), (20262, "2026-05-01")):
            out.append({"date": date, "accession": f"a{k}", "parsed": True,
                        "revenue_next_quarter": {"period_key": k, "low": 0, "high": 0, "mid": rev(k) / 1.02},
                        "operating_income_next_quarter": {"period_key": k, "low": 0, "high": 0, "mid": rev(k) * 0.6, "basis": basis}})
        mid = rev(20253) * 1.1
        out.append({"date": "2026-07-29", "accession": "g", "parsed": True,
                    "revenue_next_quarter": {"period_key": 20263, "low": 0, "high": 0, "mid": mid},
                    "operating_income_next_quarter": {"period_key": 20263, "low": 0, "high": 0, "mid": mid * 0.45, "basis": basis}})
        return out

    def test_non_gaap_operating_income_guide_is_not_used_as_gaap(self):
        world = _synth.AtlasWorld(latest=(2026, 2))
        world.releases = self.releases(world, "non_gaap")
        inp = self.fill(world)
        L = _lines(inp)
        self.assertEqual(inp["_street"]["oi_beat"], 1.0)
        self.assertAlmostEqual(L["operating_income"][20263] / L["revenue"][20263], inp["_street"]["margin_ttm"], places=9)
        self.assertTrue(any("non-GAAP" in n for n in inp["_sources"]["notes"]))
        self.assertNotIn("and operating income", inp["as_of"]["consensus_source"])

    def test_gaap_operating_income_guide_still_beat_adjusted(self):
        world = _synth.AtlasWorld(latest=(2026, 2))
        world.releases = self.releases(world, "gaap")
        inp = self.fill(world)
        L = _lines(inp)
        self.assertAlmostEqual(inp["_street"]["oi_beat"], 0.5, places=9)    # GAAP actual 30% of revenue over a 60% guide
        self.assertAlmostEqual(L["operating_income"][20263], world.releases[-1]["operating_income_next_quarter"]["mid"] * 0.5, places=6)


def _segments(world, shares, margin=0.30):
    lines = {}
    for name, share in shares.items():
        rev = {y * 10 + i: world.quarter_rev(y, i) * share for y, i in world.quarters()}
        for y in {y for y, _ in world.quarters()}:
            if all(y * 10 + i in rev for i in range(1, 5)):
                rev[y * 10] = sum(rev[y * 10 + i] for i in range(1, 5))
        lines[f"seg:{name}"] = rev
        lines[f"segoi:{name}"] = {k: v * margin for k, v in rev.items()}
    return {"defs": {name: {"parent": None, "oi_line": f"segoi:{name}"} for name in shares}, "lines": lines,
            "source": "sec.segment_facts via atlas", "members_all": list(shares), "axis": None}


class StreetSegmentsAddUp(FillCase):
    """#190: the guided quarter's total was taken uncapped and every segment was capped at ±50%, so the street segments
    summed to a fraction of the street total (MU: FY2027 Q1 69,740 against 20,464)."""

    def fill_guided(self, shares):
        world = _synth.AtlasWorld(latest=(2026, 2))
        mid = world.kpis["revenue"][20253]["value"] * 2.5
        world.releases = [{"date": "2026-07-29", "accession": "g", "parsed": True,
                           "revenue_next_quarter": {"period_key": 20263, "low": 0, "high": 0, "mid": mid}}]
        return self.fill(world, segments=_segments(world, shares))

    def test_segments_sum_to_the_street_total(self):
        inp = self.fill_guided({"Alpha": 0.6, "Beta": 0.4})
        L = _lines(inp)
        for k in (20263, 20264, 20260, 20270, 20280):
            self.assertAlmostEqual(L["seg:Alpha"][k] + L["seg:Beta"][k], L["revenue"][k], places=6, msg=k)
            self.assertAlmostEqual(L["segoi:Alpha"][k], L["seg:Alpha"][k] * 0.30, places=6, msg=k)

    def test_segments_that_cover_part_of_revenue_keep_their_share(self):
        inp = self.fill_guided({"Alpha": 0.5, "Beta": 0.3})
        L = _lines(inp)
        for k in (20263, 20264, 20260, 20270, 20280):
            self.assertAlmostEqual(L["seg:Alpha"][k] + L["seg:Beta"][k], 0.8 * L["revenue"][k], places=6, msg=k)


if __name__ == "__main__":
    unittest.main()
