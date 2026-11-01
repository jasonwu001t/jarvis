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
        self.assertAlmostEqual(st["wc_ratio"], 0.02, places=9)     # a quarter without D&A takes it at the TTM D&A ratio
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

    def test_working_capital_lines_keep_a_quarter_without_d_and_a(self):
        """The actual wc_increase quarter stays in the lines (the engine's realised ROIC and the FY0 sum read a missing one
        as zero); only the TTM ratio and median take its D&A at the TTM ratio (CRWD: a deferred-revenue build, D&A served
        in two quarters of 22)."""
        world = _synth.AtlasWorld(latest=(2026, 2), wc_share=lambda y, i: -0.10)
        del world.kpis["depreciation_amortization"][20261]
        inp = self.fill(world)
        L = _lines(inp)
        self.assertIn(20261, L["wc_increase"])
        self.assertAlmostEqual(L["wc_increase"][20262], -0.10 * world.kpis["revenue"][20262]["value"], places=6)
        self.assertAlmostEqual(inp["_street"]["wc_ratio"], -0.10, places=9)
        self.assertAlmostEqual(L["wc_increase"][20260], sum(L["wc_increase"][20260 + i] for i in range(1, 5)), places=6)
        self.assertTrue(_warned(inp, "wc_increase"))

    def test_a_seasonal_working_capital_ratio_keeps_all_four_quarters(self):
        """The GOOG / CRWD shape: D&A served in Q1-Q2 only, and in no fiscal year. Leaving those quarters out of the
        ratio kept the two building quarters of a seasonal line (+10% against a true TTM near -2%) and lost the median;
        the ratio and median take the missing D&A at the TTM D&A ratio instead."""
        world = _synth.AtlasWorld(latest=(2026, 2), wc_share=lambda y, i: 0.10 if i <= 2 else -0.14)
        for k in list(world.kpis["depreciation_amortization"]):
            if k % 10 in (0, 3, 4):
                del world.kpis["depreciation_amortization"][k]
        inp = self.fill(world)
        st, rev = inp["_street"], {k: v["value"] for k, v in world.kpis["revenue"].items()}
        last4 = (20253, 20254, 20261, 20262)
        true_ttm = sum(rev[k] * (0.10 if k % 10 <= 2 else -0.14) for k in last4) / sum(rev[k] for k in last4)
        self.assertAlmostEqual(st["da_ratio"], 0.05, places=9)
        self.assertAlmostEqual(st["wc_ratio"], true_ttm, places=9)
        self.assertAlmostEqual(st["wc_ratio_median"], -0.02, places=9)
        self.assertEqual(st["wc_median_years"], [2022, 2023, 2024, 2025])
        self.assertTrue(_warned(inp, "wc_increase", "D&A 5.00%"))
        self.assertIn(20253, _lines(inp)["wc_increase"])

    def test_no_shared_quarter_falls_back_to_the_latest_fiscal_year(self):
        world = _synth.AtlasWorld(latest=(2026, 2))
        for k in (20253, 20254, 20261, 20262):
            del world.kpis["depreciation_amortization"][k]
        inp = self.fill(world)
        self.assertAlmostEqual(inp["_street"]["da_ratio"], 0.05, places=9)
        self.assertTrue(_warned(inp, "d_and_a", "FY2025"))

    def test_the_backtest_falls_back_to_the_latest_fiscal_year_too(self):
        world = _synth.AtlasWorld(latest=(2026, 2))
        for k in (20253, 20254, 20261, 20262):
            del world.kpis["depreciation_amortization"][k]
        inp = backtest.build_inputs(_synth.engine_inputs(), _backtest_data(world), 20262, "2026-07-30", "momentum")
        L = inp["lines"]
        self.assertAlmostEqual(L["d_and_a"]["20263"] / L["revenue"]["20263"], 0.05, places=9)
        self.assertEqual(inp["_street"]["ttm_gaps"]["d_and_a / revenue"], [20250])

    def test_a_growth_with_no_year_ago_quarter_names_the_growth_used(self):
        world = _synth.AtlasWorld(latest=(2026, 2))
        segs = _segments(world, {"Alpha": 0.6, "Beta": 0.4})
        for line in ("seg:Beta", "segoi:Beta"):
            segs["lines"][line] = {k: v for k, v in segs["lines"][line].items() if k >= 20253 and k % 10}
        inp = self.fill(world, segments=segs)
        notes = _warned(inp, "seg:Beta growth")
        self.assertTrue(notes)
        self.assertIn("growth +10.0% used", notes[0])      # the momentum growth, not the factor 1.1


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

    def test_no_non_operating_line_still_charges_the_interest_expense(self):
        """MCD: no interest-income fact and no pretax line in atlas, interest expense and debt served: the fallback
        carried 0, 'annualised from 0 quarters'."""
        world = self.world()
        world.facts_rows = lambda metric: []
        del world.kpis["pretax_income"]
        inp = self.fill(world)
        oth = inp["_street"]["other_income"]
        self.assertAlmostEqual(oth["annual"], -0.04 * 1000.0, places=6)    # 40 a year on 1,000 of average debt
        self.assertIn("interest expense", oth["source"])
        self.assertNotIn("from 0 quarters", oth["source"])
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

    def test_older_gaap_guides_do_not_label_a_non_gaap_guided_quarter(self):
        world = _synth.AtlasWorld(latest=(2026, 2))
        world.releases = self.releases(world, "gaap")
        world.releases[-1]["operating_income_next_quarter"]["basis"] = "non_gaap"
        inp = self.fill(world)
        L = _lines(inp)
        self.assertAlmostEqual(L["operating_income"][20263] / L["revenue"][20263], inp["_street"]["margin_ttm"], places=9)
        self.assertNotIn("OI x", inp["as_of"]["consensus_source"])


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


def _member(name, axis, per_q, key=None):
    quarters = [{"fiscal_year": y, "fiscal_period": f"Q{i}", "value": per_q * 1e6}
                for y in (2025, 2026) for i in (1, 2, 3, 4) if (y, i) <= (2026, 2)]
    m = {"member": name, "member_key": key or name.lower(), "revenue": {"quarterly": quarters, "annual": []},
         "operating_income": {"quarterly": [], "annual": []}}
    if axis:
        m["axis"] = axis
    return m


class SegmentAxes(unittest.TestCase):
    """#142: a 6-K filer's members come on several axes (geography, platform, product, technology); segments() made
    every one a business line keyed by the bare name, so 'Others' held whichever axis came last (TSM: 19 'segments'
    summing to 3.7x revenue)."""

    def setUp(self):
        self.saved = atlas_data.get

    def tearDown(self):
        atlas_data.get = self.saved

    def serve(self, members, axis="statements note"):
        atlas_data.get = lambda path, **kw: {"data": {"axis": axis, "segments": members, "source": "sec.foreign_quarterly_statements"}}

    def six_k(self):
        return [_member("Taiwan", "geography", 60.0), _member("Others", "geography", 40.0),
                _member("HPC", "platform", 70.0), _member("Others", "platform", 30.0),
                _member("3nm", "technology", 50.0), _member("5nm", "technology", 30.0)]

    def test_one_axis_becomes_the_business_lines(self):
        self.serve(self.six_k())
        S = atlas_data.segments("ZZZ")
        self.assertEqual(S["axis"], "platform")
        self.assertEqual(sorted(S["defs"]), ["HPC", "Others"])
        self.assertEqual(S["lines"]["seg:Others"][20262], 30.0)
        self.assertEqual(sum(S["lines"][f"seg:{n}"][20262] for n in S["defs"]), 100.0)
        self.assertIn("platform", S["source"])
        self.assertEqual(sorted(S["axes"]), ["geography", "platform", "technology"])

    def test_the_caller_picks_another_axis(self):
        self.serve(self.six_k())
        S = atlas_data.segments("ZZZ", axis="geography")
        self.assertEqual(sorted(S["defs"]), ["Others", "Taiwan"])
        self.assertEqual(S["lines"]["seg:Others"][20262], 40.0)

    def test_a_us_filer_keeps_its_single_axis(self):
        self.serve([_member("Cloud", None, 60.0), _member("Devices", None, 40.0)], axis="us-gaap:StatementBusinessSegmentsAxis")
        S = atlas_data.segments("ZZZ")
        self.assertEqual(sorted(S["defs"]), ["Cloud", "Devices"])
        self.assertEqual(S["axis"], "us-gaap:StatementBusinessSegmentsAxis")

    def test_a_repeated_name_on_one_axis_does_not_overwrite(self):
        members = [_member("Other", None, 60.0, key="other_a"), _member("Other", None, 40.0, key="other_b")]
        for order in (members, members[::-1]):          # the names do not depend on the row order
            self.serve(order)
            S = atlas_data.segments("ZZZ")
            self.assertEqual(sorted(S["defs"]), ["Other (other_a)", "Other (other_b)"])
            self.assertEqual(S["lines"]["seg:Other (other_a)"][20262], 60.0)

    def test_the_axis_that_adds_up_to_revenue_is_chosen(self):
        self.serve([_member("HPC", "platform", 60.0),                    # a platform member not served: 60 of 100
                    _member("Wafer", "product", 90.0), _member("Others", "product", 10.0)])
        self.assertEqual(atlas_data.segments("ZZZ")["axis"], "platform")
        S = atlas_data.segments("ZZZ", revenue={20262: 100.0})
        self.assertEqual((S["axis"], sorted(S["defs"])), ("product", ["Others", "Wafer"]))
        self.assertEqual(atlas_data.segments("ZZZ", revenue={20262: 300.0})["axis"], "platform")   # none adds up: preference


class SegmentSumCheck(FillCase):
    """#142: the fill says which axis it used and warns when the segment lines do not add up to revenue."""

    def test_the_fill_names_the_axis_and_warns_on_a_short_sum(self):
        world = _synth.AtlasWorld(latest=(2026, 2))
        segs = {**_segments(world, {"Alpha": 0.5, "Beta": 0.2}), "axis": "platform",
                "source": "sec.foreign_quarterly_statements via atlas, platform axis"}
        inp = self.fill(world, segments=segs)
        self.assertIn("platform", inp["_sources"]["segments"])
        self.assertTrue(_warned(inp, "segments", "70"))

    def test_the_check_uses_the_latest_quarter_the_segments_have(self):
        """TSM: the platform axis stops a quarter before revenue, and lacks the year-ago quarter of the next one."""
        world = _synth.AtlasWorld(latest=(2026, 2))
        segs = _segments(world, {"Alpha": 0.5, "Beta": 0.2})
        for line in segs["lines"].values():
            line.pop(20262), line.pop(20253)
        inp = self.fill(world, segments=segs)
        self.assertTrue(_warned(inp, "segments", "70%", "20261"))
        self.assertTrue(_warned(inp, "no FY2026 street value", "20262", "20263"))

    def test_an_axis_without_members_is_said(self):
        world = _synth.AtlasWorld(latest=(2026, 2))
        segs = {"defs": {}, "lines": {}, "axis": None, "axes": {"geography": ["Taiwan"], "technology": ["3nm"]},
                "members_all": [], "latest_keys": [], "source": "sec.foreign_quarterly_statements via atlas"}
        inp = self.fill(world, segments=segs)
        self.assertTrue(_warned(inp, "segment", "geography", "technology"))


META_CAPEX = ("We anticipate 2026 capital expenditures, including principal payments on finance leases, to be in the range "
              "of $135-145 billion, narrowed from our prior outlook of $130-145 billion.")
PLAIN_CAPEX = "With the growth across our business we now expect 2026 capital expenditures to be in a range of $91-93 billion."


class CapexGuideBasis(unittest.TestCase):
    """#99: a capex guide 'including principal payments on finance leases' lost that qualifier; the report compared it
    with lease-free capex under a hard-coded '(incl. finance leases)' label and the backtest added leases on top."""

    def test_parse_and_atlas_rows_carry_the_flag(self):
        self.assertTrue(guidance.parse(META_CAPEX)["capex_full_year"]["includes_finance_lease_principal"])
        self.assertFalse(guidance.parse(PLAIN_CAPEX)["capex_full_year"]["includes_finance_lease_principal"])
        row = {"accession_number": "a1", "knowledge_time": "2026-10-29T13:00:00", "period_key": 20260, "metric": "capex",
               "period_kind": "fiscal_year", "low": 135e9, "high": 145e9, "mid": 140e9, "unit": "USD", "basis": "gaap",
               "source_text": META_CAPEX}
        saved = atlas_data.get
        atlas_data.get = lambda path, **kw: {"data": {"columns": [{"name": c} for c in row], "rows": [list(row.values())]}}
        try:
            cx = atlas_data.guidance_releases("ZZZ")[0]["capex_full_year"]
        finally:
            atlas_data.get = saved
        self.assertTrue(cx["includes_finance_lease_principal"])

    def test_the_whole_sentence_is_read_and_a_negation_is_not_a_flag(self):
        flag = lambda text: guidance.parse(text)["capex_full_year"]["includes_finance_lease_principal"]
        self.assertTrue(flag("Including principal payments on finance leases, we expect 2026 capital expenditures to be "
                             "in the range of $135-145 billion."))
        self.assertFalse(flag("We expect 2026 capital expenditures, not including finance leases, to be in the range of "
                              "$135-145 billion."))
        self.assertFalse(flag("Lease costs, including finance leases, rose. We expect 2026 capital expenditures to be in the "
                              "range of $91-93 billion."))

    def guided(self, flag):
        inp = _synth.engine_inputs()
        inp["lines"]["finance_lease_additions"]["20260"] = 500.0
        cx = {"period_key": 20260, "low": 1000.0, "high": 1100.0, "mid": 1050.0, "includes_finance_lease_principal": flag}
        live = {"guidance": {"parsed": True, "date": "2026-07-29", "capex_full_year": cx}}
        return inp, mm.Model(inp).run(), live

    def test_report_and_monitor_compare_like_with_like(self):
        inp, out, live = self.guided(True)
        capex = inp["lines"]["capex"]["20260"]
        page = report_html.position_section(inp, out, live)
        self.assertIn("(incl. finance leases)", page)
        self.assertIn(report_html.m(capex + 500.0), page)
        md = monitor.render(inp, out, live, [], {}, [])
        self.assertIn(monitor.money(capex + 500.0), md)
        inp, out, live = self.guided(False)
        page = report_html.position_section(inp, out, live)
        self.assertNotIn("(incl. finance leases)", page)
        self.assertIn(report_html.m(capex), page)

    def test_backtest_street_capex_excludes_the_lease_share(self):
        world = _synth.AtlasWorld(latest=(2026, 2))
        mid = 1200.0
        data = _backtest_data(world, [{"date": "2026-07-29", "revenue_next_quarter": {"period_key": 20263, "mid": 1400.0},
                                       "capex_full_year": {"period_key": 20260, "mid": mid, "includes_finance_lease_principal": True}}])
        for r in data["kpis"]["finance_lease_additions"]:
            r["value"] = next(c["value"] for c in data["kpis"]["capex"] if c["key"] == r["key"]) * 0.10    # leases 10% of capex
        inp = backtest.build_inputs(_synth.engine_inputs(), data, 20262, "2026-07-30", "guidance")
        L = inp["lines"]
        self.assertAlmostEqual(L["capex"]["20260"] + L["finance_lease_additions"]["20260"], mid, places=6)
        data["guidance"][0]["capex_full_year"]["includes_finance_lease_principal"] = False
        L = backtest.build_inputs(_synth.engine_inputs(), data, 20262, "2026-07-30", "guidance")["lines"]
        self.assertAlmostEqual(L["capex"]["20260"], mid, places=6)


if __name__ == "__main__":
    unittest.main()
