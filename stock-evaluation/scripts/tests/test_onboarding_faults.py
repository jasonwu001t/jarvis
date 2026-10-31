"""The nine skill faults the 2026-10-25 onboardings (AVGO, MU, CRWD, ANET) recorded, one test class each, on synthetic
companies (tests/_synth.py). Run with `python3 -m unittest discover -s scripts/tests` (or pytest) from the skill root."""
import contextlib
import datetime as dt
import io
import json
import os
import shutil
import statistics
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _synth  # noqa: E402
import fill_from_atlas  # noqa: E402
import monitor  # noqa: E402
import new_ticker  # noqa: E402
import report_html  # noqa: E402
import thesis_tracker  # noqa: E402
import valuation_engine as mm  # noqa: E402


def _check(out, prefix):
    return next(c for c in out["checks"] if c["check"].startswith(prefix))


class FillCase(unittest.TestCase):
    """Runs fill_from_atlas.main on a scaffolded folder against an AtlasWorld."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dir = os.path.join(self.tmp, "ZZZ")
        with contextlib.redirect_stdout(io.StringIO()):
            new_ticker.main(["ZZZ", "Synthetic Co", "--dir", self.dir])
        self._saved = (fill_from_atlas.atlas_data.fundamentals, fill_from_atlas.atlas_data.segments,
                       fill_from_atlas.atlas_data.guidance_releases, fill_from_atlas.get, fill_from_atlas.guid.collect)

    def tearDown(self):
        (fill_from_atlas.atlas_data.fundamentals, fill_from_atlas.atlas_data.segments,
         fill_from_atlas.atlas_data.guidance_releases, fill_from_atlas.get, fill_from_atlas.guid.collect) = self._saved
        shutil.rmtree(self.tmp)

    def fill(self, world, *args):
        def no_segments(ticker, **kw):
            raise fill_from_atlas.atlas_data.NotCollected("no segment facts")
        fill_from_atlas.atlas_data.fundamentals = world.fundamentals
        fill_from_atlas.atlas_data.segments = no_segments
        fill_from_atlas.atlas_data.guidance_releases = lambda ticker, since=None: list(world.releases)
        fill_from_atlas.get = world.get
        fill_from_atlas.guid.collect = lambda *a, **kw: []
        with contextlib.redirect_stdout(io.StringIO()):
            fill_from_atlas.main(["--dir", self.dir, "--since-fy", "2023", *args])
        return json.load(open(os.path.join(self.dir, "inputs.json"), encoding="utf-8"))


# ---------------------------------------------------------------------------------------------- (1)
class Q4LatestFill(FillCase):
    """A fill whose latest quarter is Q4 lists each fiscal year once, starts the street from the guided quarter and caps
    the momentum it extrapolates (MU: FY2026 listed twice, +256% momentum)."""

    @staticmethod
    def runaway(y, i):
        return {2026: [2000.0, 2500.0, 3000.0, 3500.0]}.get(y, [1000.0] * 4)[i - 1]

    def releases(self):
        past = [{"date": f"{y}-{3 * i + 1:02d}-25", "accession": f"a{y}{i}", "parsed": True,
                 "revenue_next_quarter": {"period_key": y * 10 + i, "low": 0, "high": 0, "mid": self.runaway(y, i) / 1.02}}
                for y, i in ((2025, 3), (2025, 4), (2026, 1), (2026, 2), (2026, 3), (2026, 4))]
        return past + [{"date": "2027-01-28", "accession": "g", "parsed": True,
                        "revenue_next_quarter": {"period_key": 20271, "low": 3900.0, "high": 4100.0, "mid": 4000.0}}]

    def test_each_year_once_and_street_from_guided_quarter(self):
        world = _synth.AtlasWorld(latest=(2026, 4), quarter_rev=self.runaway, releases=self.releases())
        inp = self.fill(world)
        keys = [p["key"] for p in inp["periods"]]
        self.assertEqual(len(keys), len(set(keys)), "a fiscal year is listed twice")
        status = {p["key"]: p["status"] for p in inp["periods"]}
        self.assertEqual(status[20260], "actual")
        self.assertEqual(status[20270], "consensus")
        self.assertEqual(status[20280], "consensus")
        self.assertFalse([k for k in keys if k // 10 == 2027 and k % 10], "FY+1 quarters are lines, not periods")
        L = {line: {int(k): v for k, v in vals.items()} for line, vals in inp["lines"].items()}
        self.assertAlmostEqual(L["net_income"][20260], world.kpis["net_income"][20260]["value"], places=4)   # the actual year is not rebuilt
        self.assertAlmostEqual(L["revenue"][20271], 4000.0 * 1.02, places=3)                                # the guided quarter, beat-adjusted
        self.assertAlmostEqual(L["revenue"][20270], sum(L["revenue"][20270 + i] for i in range(1, 5)), places=3)
        self.assertAlmostEqual(L["revenue"][20272] / L["revenue"][20262] - 1, 0.5, places=6)               # +104% guided y/y, capped at 50%
        self.assertAlmostEqual(L["revenue"][20280] / L["revenue"][20270] - 1, 0.5 * 0.8, places=6)
        self.assertEqual(inp["_street"]["growth_cap"], 0.5)
        self.assertGreater(inp["_street"]["g_uncapped"], 0.5)
        self.assertIn("cap", inp["as_of"]["consensus_source"])

    def test_momentum_without_a_guide_is_capped(self):
        world = _synth.AtlasWorld(latest=(2026, 4), quarter_rev=self.runaway)
        inp = self.fill(world)
        rev = {int(k): v for k, v in inp["lines"]["revenue"].items()}
        self.assertAlmostEqual(rev[20270] / rev[20260] - 1, 0.5, places=6)        # +175% closed-year momentum, capped
        self.assertEqual(sorted(p["key"] for p in inp["periods"] if p["status"] != "actual"), [20270, 20280])


# ---------------------------------------------------------------------------------------------- (2)
class NegativeEarningsBase(unittest.TestCase):
    """A negative or near-zero earnings base disables the P/E leg for that scenario, moves its weight to the DCF and says
    so; never a negative P/E target (CRWD)."""

    def test_loss_maker(self):
        inp = _synth.engine_inputs(fc_margin=-0.05)
        out = mm.Model(inp).run()
        for k in mm.SCENARIOS:
            sc = out["scenarios"][k]
            self.assertTrue(sc["multiples"]["disabled"])
            self.assertIsNone(sc["multiples"]["target"])
            self.assertAlmostEqual(sc["blended_target"], sc["dcf"]["target"], places=6)
        self.assertTrue(any("P/E leg disabled" in w and "bear" in w for w in out["warnings"]))
        page = report_html.render(inp, out, {}, [], {}, [], [], None)
        self.assertIn("WARNING", page)
        self.assertIn("P/E leg disabled", page)
        md = monitor.render(inp, out, {}, [], {}, [])
        self.assertIn("## Warnings", md)

    def test_near_zero_base(self):
        out = mm.Model(_synth.engine_inputs(fc_margin=0.005)).run()      # net margin 0.4% after tax
        self.assertTrue(out["scenarios"]["base"]["multiples"]["disabled"])

    def test_profitable_base_untouched(self):
        out = mm.Model(_synth.engine_inputs()).run()
        for k in mm.SCENARIOS:
            m = out["scenarios"][k]["multiples"]
            self.assertFalse(m["disabled"])
            self.assertGreater(m["target"], 0)
        self.assertEqual(out["warnings"], [])


# ---------------------------------------------------------------------------------------------- (3)
class MissingCostOfDebt(unittest.TestCase):
    """A null pretax_cost_of_debt falls back to the risk-free rate plus a stated spread with a WARNING (monitor crashed)."""

    def test_fallback(self):
        inp = _synth.engine_inputs(cost_of_debt=None)
        out = mm.Model(inp).run()
        self.assertAlmostEqual(out["wacc"]["pretax_cost_of_debt"], 0.04 + 0.015, places=9)
        self.assertTrue(any("cost of debt" in w for w in out["warnings"]))
        inp["wacc"]["debt_spread"] = 0.02
        self.assertAlmostEqual(mm.Model(inp).run()["wacc"]["pretax_cost_of_debt"], 0.06, places=9)
        page = report_html.render(inp, mm.Model(inp).run(), {}, [], {}, [], [], None)
        self.assertIn("risk-free + 2.00% spread", page)

    def test_stated_rate_kept(self):
        out = mm.Model(_synth.engine_inputs(cost_of_debt=0.045)).run()
        self.assertAlmostEqual(out["wacc"]["pretax_cost_of_debt"], 0.045, places=9)
        self.assertFalse(any("cost of debt" in w for w in out["warnings"]))


# ---------------------------------------------------------------------------------------------- (4) and (5)
class StreetOtherIncomeAndWorkingCapital(FillCase):
    def world(self):
        # working capital 2-3% of revenue in FY2022-24, a spike to 10% over the last four quarters
        def wc(y, i):
            if (y, i) >= (2025, 3):
                return 0.10
            return {2022: 0.02, 2023: 0.03, 2024: 0.025, 2025: 0.025}[y]
        return _synth.AtlasWorld(latest=(2026, 2), wc_share=wc, cash=4000.0, debt=1000.0, interest_income=40.0, interest_expense=10.0)

    def test_other_income_follows_interest_on_cash(self):
        """(4) forecast other income = the last four quarters' interest income yield on the carried cash balance, net of
        interest expense at its TTM rate on the carried debt, labelled (it was 0)."""
        inp = self.fill(self.world())
        oi = {int(k): v for k, v in inp["lines"]["other_income"].items()}
        annual = 0.04 * 4000.0 - 0.04 * 1000.0
        self.assertAlmostEqual(oi[20270], annual, places=6)
        self.assertAlmostEqual(oi[20280], annual, places=6)
        self.assertAlmostEqual(oi[20263], annual / 4, places=6)
        L = inp["lines"]
        self.assertAlmostEqual(L["pretax_income"]["20270"], L["operating_income"]["20270"] + annual, places=6)
        lab = inp["_street"]["other_income"]
        self.assertAlmostEqual(lab["interest_income_ttm"], 160.0, places=6)    # Q4 derived as the year less Q1-Q3
        self.assertIn("InvestmentIncomeInterest", lab["source"])
        self.assertIn("interest income", inp["as_of"]["consensus_source"])

    def test_working_capital_reverts_to_historical_median(self):
        """(5) the street's working capital moves from the TTM share to the historical median share by FY+2 (it was the
        TTM share in every period)."""
        inp = self.fill(self.world())
        L = inp["lines"]
        share = lambda k: L["wc_increase"][str(k)] / L["revenue"][str(k)]
        med = statistics.median([0.02, 0.03, 0.025, (0.025 + 0.10) / 2])
        self.assertAlmostEqual(share(20263), 0.10, places=6)                 # the rest of the current year: TTM share
        self.assertAlmostEqual(share(20270), (0.10 + med) / 2, places=6)
        self.assertAlmostEqual(share(20280), med, places=6)
        self.assertAlmostEqual(inp["_street"]["wc_ratio_median"], med, places=6)


# ---------------------------------------------------------------------------------------------- (6)
class ScaffoldStretchedRule(unittest.TestCase):
    def test_scaffold_writes_stretched(self):
        tmp = tempfile.mkdtemp()
        try:
            d = os.path.join(tmp, "ZZZ")
            with contextlib.redirect_stdout(io.StringIO()):
                new_ticker.main(["ZZZ", "Synthetic Co", "--dir", d])
            inp = json.load(open(os.path.join(d, "inputs.json"), encoding="utf-8"))
            rules = {r["name"]: r for r in inp["monitor"]["rules"]}
            self.assertIn("Stretched", rules)
            st = rules["Stretched"]
            self.assertIsNotNone(st.get("exposure"))
            self.assertTrue(eval(st["when"], {"__builtins__": {}}, {"house_upside": -0.2}))
            self.assertFalse(eval(st["when"], {"__builtins__": {}}, {"house_upside": 0.0}))
            for c in inp["thesis"]["claims"]:
                if (c.get("check") or {}).get("kind") == "rule":
                    self.assertIn(c["check"]["name"], rules)
        finally:
            shutil.rmtree(tmp)


# ---------------------------------------------------------------------------------------------- (7)
class ReportSegmentRows(unittest.TestCase):
    def test_rows_from_segments_block(self):
        segs = {"Widgets": {"parent": None, "oi_line": "segoi:Widgets"}, "Premium": {"parent": "Widgets"},
                "Gadgets": {"parent": None, "oi_line": "segoi:Gadgets"}}
        rows = report_html.row_specs(segs)["income"]
        labels = {r[1]: r[0] for r in rows if r[1]}
        self.assertEqual(labels["seg:Widgets"], "Widgets revenue")
        self.assertEqual(labels["seg:Premium"].strip(), "Premium")
        self.assertTrue(labels["seg:Premium"].startswith("  "))
        self.assertIn("segoi:Gadgets", labels)
        self.assertIn("yoy:seg:Gadgets", labels)
        self.assertFalse([r for r in rows if r[1] and "Family of Apps" in r[1]])

    def test_report_and_engine_use_the_folder_segments(self):
        inp = _synth.engine_inputs(segments={"Widgets": 0.6, "Gadgets": 0.4})
        out = mm.Model(inp).run()
        T = mm.Model(inp).table("base")
        self.assertTrue("yoy:seg:Widgets" in T)
        page = report_html.render(inp, out, {}, [], {}, [], [], None)
        self.assertIn("Widgets revenue", page)
        self.assertIn("Gadgets operating income", page)
        self.assertNotIn("Family of Apps", page)


# ---------------------------------------------------------------------------------------------- (8)
class CompanyTypeChecks(unittest.TestCase):
    """The ROIC and reinvestment checks take the company type into account and say which rule they used."""

    def test_cyclical_steady_roic_through_cycle(self):
        # bear steady ROIC 8% sits below the ~8.9% WACC; the probability-weighted average (18%) is above it
        cyc = mm.Model(_synth.engine_inputs(year_growth={2024: -0.30}, roic=(0.08, 0.20, 0.25))).run()
        c = _check(cyc, "Steady-state ROIC at or above WACC")
        self.assertTrue(c["ok"], c)
        self.assertIn("cyclical", c["check"])
        self.assertIn("rule", c["check"])
        r = _check(cyc, "Realised")
        self.assertIn("through-cycle", r["check"])
        std = mm.Model(_synth.engine_inputs(roic=(0.08, 0.20, 0.25))).run()
        c = _check(std, "Steady-state ROIC at or above WACC")
        self.assertFalse(c["ok"])
        self.assertIn("standard", c["check"])

    def test_cyclical_transition_return_through_cycle(self):
        inp = _synth.engine_inputs(year_growth={2024: -0.30})
        m = mm.Model(inp)
        out = m.run()
        c = _check(out, "Implied return on new investment")
        self.assertIn("through-cycle", c["check"])
        # revenue added through the transition at the steady margin after tax, per dollar of cumulative reinvestment
        s, e, S = out["scenarios"]["base"]["series"], out["scenarios"]["base"]["extrapolation"], inp["scenarios"]["base"]
        y2, last = m.last_explicit, m.years_ext[-1][0]
        reinv = lambda src, k: src["capex"][k] + src["finance_lease_additions"][k] - src["d_and_a"][k] + src["wc_increase"][k]
        tot = reinv(s, y2) + sum(reinv(e, yk) for yk, _ in m.years_ext)
        want = (e["revenue"][last] * (1 + S["terminal_growth"]) - s["revenue"][y2]) * S["steady_margin"] * (1 - S["steady_tax"]) / tot
        self.assertAlmostEqual(c["value"], want, places=9)

    def test_deferred_revenue_negative_working_capital_allowed(self):
        inp = _synth.engine_inputs(wc_share=-0.10, capex_share=0.12)
        out = mm.Model(inp).run()
        c = _check(out, "Starting reinvestment rate")
        self.assertIn("deferred-revenue", c["check"])
        self.assertTrue(c["ok"], c)          # (12% capex − 5% D&A) / revenue, the −10% working capital not counted against it
        inp["company"]["business_model"] = "standard"
        c = _check(mm.Model(inp).run(), "Starting reinvestment rate")
        self.assertFalse(c["ok"])
        self.assertIn("standard", c["check"])

    def test_declared_type_wins(self):
        inp = _synth.engine_inputs(roic=(0.08, 0.20, 0.25))
        inp["company"]["business_model"] = "cyclical"
        c = _check(mm.Model(inp).run(), "Steady-state ROIC at or above WACC")
        self.assertTrue(c["ok"])
        self.assertIn("declared", c["check"])


# ---------------------------------------------------------------------------------------------- (9)
class ZeroFloorBand(unittest.TestCase):
    def status(self, mn, tol, margin):
        inp = {"as_of": {"latest_reported_fy": 2026, "latest_reported_q": 2, "balance_sheet_date": "2026-06-30"},
               "thesis": {"claims": [{"id": "m", "claim": "margin", "check": {"kind": "margin", "num": "operating_income",
                                                                               "den": "revenue", "min": mn, "tolerance": tol}}]}}
        mi = {"as_of": inp["as_of"], "lines": {"revenue": {"20262": 1000.0}, "operating_income": {"20262": margin * 1000.0}}}
        return thesis_tracker.evaluate_claims(inp, mi, {}, dt.date(2026, 10, 25))[0]["status"]

    def test_zero_floor_has_a_near_miss_band(self):
        self.assertEqual(self.status(0.0, 0.05, -0.023), "watch")     # CRWD's GAAP break-even claim scored Broken
        self.assertEqual(self.status(0.0, 0.05, -0.08), "broken")
        self.assertEqual(self.status(0.0, 0.05, 0.01), "on_track")

    def test_nonzero_floor_unchanged(self):
        self.assertEqual(self.status(0.40, 0.05, 0.385), "watch")
        self.assertEqual(self.status(0.40, 0.05, 0.37), "broken")


if __name__ == "__main__":
    unittest.main()
