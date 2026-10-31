"""Engine and report faults of the 2026-10-26 bug audit (#91, #92, #254, #255, #256, #191, #189, #22) on synthetic
inputs. Run with `python3 -B -m unittest discover -s scripts/tests` from the skill root."""
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _synth  # noqa: E402
import report_html  # noqa: E402
import thesis_tracker as tt  # noqa: E402
import valuation_engine as mm  # noqa: E402

STOCKS = ("diluted_shares", "dps", "cash_and_st_investments", "debt", "investments", "minority_interest", "equity")


def with_extra_years(inp, n=2, growth=0.08):
    """Consensus annual periods after FY+2 (a street to FY+4, say), every flow growing `growth` a year."""
    prev = (inp["as_of"]["latest_reported_fy"] + 2) * 10
    for j in range(1, n + 1):
        k = prev + 10
        for line, vals in inp["lines"].items():
            v = vals.get(str(prev))
            if v is not None:
                vals[str(k)] = v if line in STOCKS else v * (1 + growth)
        inp["periods"].append({"key": k, "year": k // 10, "q": 0, "status": "consensus"})
        prev = k
    return inp


def exit_pe_inputs(**kw):
    inp = _synth.engine_inputs(**kw)
    inp["blend"].update(terminal_mode="exit_pe", convergence_years=0)
    for k, pe in zip(mm.SCENARIOS, (15, 20, 25)):
        inp["scenarios"][k]["exit_pe"] = pe
    return inp


def anchored_inputs(roic=(0.12, 0.20, 0.25), capex_share=0.06):
    inp = _synth.engine_inputs(roic=roic, capex_share=capex_share)
    inp["blend"]["steady_roic_anchor"] = {"enabled": True, "years": 2, "floor_over_wacc": 0.02}
    return inp


def chart_data(page):
    return json.loads(re.search(r"const D=(\{.*?\});\n", page).group(1))


def highlighted(html):
    """The first highlighted cell of the sensitivity block: the steady ROIC x margin (or exit P/E x WACC) grid's."""
    return re.search(r"class='num hl'>([^<]+)<", html).group(1)


class ReverseDcfGrowthCoversEveryForecastYear(unittest.TestCase):
    """#91: implied() added the solved growth only to the current FY's quarters, FY+1 and FY+2, so consensus years after
    FY+2 kept their growth while every page said 'pp in every forecast period'; the tornado's break-even disagreed."""

    def test_the_engine_and_the_tornado_solve_the_same_growth(self):
        inp = with_extra_years(exit_pe_inputs())
        price = mm.Model(inp).run()["scenarios"]["base"]["blended_target"] * 0.8
        engine = mm.Model(inp).implied(price)["growth_pp"]
        tornado = tt._solve(lambda x: tt._targets(tt._perturb(inp, "growth_pp", x))["base"], price, -0.30, 0.30)
        self.assertIsNotNone(engine)
        self.assertAlmostEqual(engine, tornado, delta=0.001)


class ExitPeOwnsItsTimeline(unittest.TestCase):
    """#92: exit_pe's terminal value already covers every year after the last explicit one, yet a non-zero
    convergence_years (the scaffold's 12) still added the transition years' FCFF on top, without a word."""

    def test_the_value_does_not_depend_on_convergence_years(self):
        runs = {}
        for conv in (0, 12, None):
            inp = exit_pe_inputs()
            if conv is None:
                del inp["blend"]["convergence_years"]
            else:
                inp["blend"]["convergence_years"] = conv
            runs[conv] = mm.Model(inp).run()
        base = runs[0]["scenarios"]["base"]["dcf"]
        for conv in (12, None):
            d = runs[conv]["scenarios"]["base"]["dcf"]
            self.assertAlmostEqual(d["enterprise_value"], base["enterprise_value"], places=6)
            self.assertAlmostEqual(d["target"], base["target"], places=6)
            self.assertEqual(d["pv_stage2"], 0)
        self.assertTrue(any("convergence_years" in w for w in runs[12]["warnings"]))
        self.assertFalse(any("convergence_years" in w for w in runs[0]["warnings"]))
        out = runs[12]
        bridge = report_html.bridge_table(out["scenarios"]["base"], out["wacc"], exit_pe_inputs()["scenarios"]["base"],
                                          out["price"], "Base", exit_pe_inputs()["blend"])
        self.assertIn("through FY2028", bridge)


class AnchorFloorOnlyLimitsTheShift(unittest.TestCase):
    """#254: the anchor lifted any scenario below WACC + floor_over_wacc to the floor even when it did not bind
    (delta 0), and reported an anchored_base different from the ROIC the run used."""

    def test_a_scenario_below_the_floor_keeps_its_value_when_the_anchor_does_not_bind(self):
        inp = anchored_inputs(roic=(0.06, 0.20, 0.25))
        out = mm.Model(inp).run()
        anchor = out["returns"]["anchor"]
        self.assertEqual(anchor["delta"], 0)
        self.assertGreater(anchor["floor"], 0.06)
        plain = mm.Model(_synth.engine_inputs(roic=(0.06, 0.20, 0.25))).run()
        self.assertAlmostEqual(out["scenarios"]["bear"]["dcf"]["target"], plain["scenarios"]["bear"]["dcf"]["target"], places=6)
        self.assertEqual(out["effective_scenarios"]["bear"]["steady_roic"], 0.06)

    def test_the_reported_anchored_base_is_the_roic_used(self):
        out = mm.Model(anchored_inputs(roic=(0.06, 0.10, 0.25))).run()
        self.assertEqual(out["returns"]["anchor"]["anchored_base"], out["returns"]["steady_roic_base"])
        self.assertEqual(out["returns"]["steady_roic_base"], 0.10)

    def test_a_binding_anchor_stops_at_the_floor(self):
        # unchanged behaviour, kept as a guard: a shift past the floor stops at the floor
        out = mm.Model(anchored_inputs(roic=(0.15, 0.30, 0.40), capex_share=0.60)).run()
        anchor = out["returns"]["anchor"]
        self.assertLess(anchor["incremental_roic"], anchor["floor"])
        self.assertAlmostEqual(out["returns"]["steady_roic_base"], anchor["floor"], places=12)
        self.assertAlmostEqual(out["effective_scenarios"]["bear"]["steady_roic"], anchor["floor"], places=12)
        self.assertAlmostEqual(out["effective_scenarios"]["bull"]["steady_roic"], 0.40 + anchor["delta"], places=12)


class HouseImpliedMultipleInPriceCurrency(unittest.TestCase):
    """#255: the house implied multiple divided a price-currency, per-listed-share target by model-currency NI per
    ordinary share, so it was off by fx x adr_ratio for any ADR or local-currency model."""

    def test_the_multiple_does_not_move_with_fx_and_the_adr_ratio(self):
        plain = mm.Model(_synth.engine_inputs()).run()["house"]["implied_multiple"]
        inp = _synth.engine_inputs()
        inp["market"].update(fx=0.031, adr_ratio=5.0, price=inp["market"]["price"] * 0.031 * 5.0)
        out = mm.Model(inp).run()
        self.assertAlmostEqual(out["house"]["implied_multiple"], out["scenarios"]["base"]["multiples"]["target_multiple"], places=9)
        self.assertAlmostEqual(out["house"]["implied_multiple"], plain, places=9)


class EarningsBasisIsNormalised(unittest.TestCase):
    """#256: earnings_basis was compared to 'GAAP' exactly, so 'gaap' (TSM) or 'IFRS' valued the P/E leg on
    adjusted net income."""

    def pe_target(self, basis):
        inp = _synth.engine_inputs()
        for k in (inp["as_of"]["latest_reported_fy"] + 1, inp["as_of"]["latest_reported_fy"] + 2):
            inp["lines"]["adjustments"][str(k * 10)] = 500.0
        inp["blend"]["earnings_basis"] = basis
        return mm.Model(inp).run()["scenarios"]["base"]["multiples"]

    def test_reported_spellings_value_net_income(self):
        gaap = self.pe_target("GAAP")
        for basis in ("gaap", "IFRS", " Gaap "):
            mu = self.pe_target(basis)
            self.assertAlmostEqual(mu["target"], gaap["target"], places=9)
            self.assertEqual(mu["basis"], basis)

    def test_adjusted_spellings_value_adjusted_net_income(self):
        adjusted = self.pe_target("adjusted")
        self.assertGreater(adjusted["target"], self.pe_target("GAAP")["target"])
        for basis in ("non-GAAP", "Non_GAAP"):
            self.assertAlmostEqual(self.pe_target(basis)["target"], adjusted["target"], places=9)

    def test_an_unknown_basis_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            self.pe_target("bogus")
        self.assertIn("bogus", str(caught.exception))


class ReportedYearAfterAFourthQuarter(unittest.TestCase):
    """#191: after a Q4 the fully reported fiscal year was labelled 'FY2026E' and charted as a DCF forecast bar."""

    def test_the_year_is_actual_and_the_forecast_chart_starts_next_year(self):
        inp = _synth.engine_inputs(fy=2026, q=4)
        model = mm.Model(inp)
        col = next(c for c in model.period_meta() if c["key"] == 20260)
        self.assertEqual((col["label"], col["status"]), ("FY2026", "actual"))
        out = mm.Model(inp).run()
        tables = {k: model.table(k) for k in report_html.SCN}
        data = json.loads(report_html.chart_payload(model, out, tables, inp))
        self.assertEqual(data["fc"]["labels"][0], "FY2027")
        self.assertEqual(data["rev"]["labels"][data["rev"]["n_hist"] - 1], "FY2026")
        self.assertEqual(data["rev"]["labels"].count("FY2026"), 1)
        self.assertNotIn("FY2026E", report_html.render(inp, out, {}, [], {}, [], [], None))

    def test_a_year_in_progress_stays_a_forecast(self):
        col = next(c for c in mm.Model(_synth.engine_inputs(fy=2026, q=2)).period_meta() if c["key"] == 20260)
        self.assertEqual((col["label"], col["status"]), ("FY2026E", "forecast"))


class ReportFollowsTheAnchor(unittest.TestCase):
    """#189: the report rebuilt its tables, labels and sensitivities from the template steady ROIC, while the DCF it
    stated used the anchored one."""

    def test_tables_labels_and_grid_use_the_anchored_roic(self):
        inp = anchored_inputs(capex_share=0.20)
        out = mm.Model(inp).run()
        anchor = out["returns"]["anchor"]
        self.assertLess(anchor["delta"], 0)
        roic = out["returns"]["steady_roic_base"]
        page = report_html.render(inp, out, {}, [], {}, [], [], None)
        self.assertIn(f"g {report_html.pc(0.035)}, ROIC {report_html.pc(roic, 0)}", page)
        self.assertNotIn(f"g {report_html.pc(0.035)}, ROIC {report_html.pc(0.20, 0)}", page)
        d = out["scenarios"]["base"]["dcf"]
        fcff = {r["period"]: r["fcff"] for r in d["rows"] if r["stage"] == 2}
        data = chart_data(page)
        charted = dict(zip(data["fc"]["labels"], data["fc"]["base"]))
        for k, v in fcff.items():
            self.assertAlmostEqual(charted[f"FY{k // 10}"], v, places=6)
        sn = report_html.sensitivities(inp, out)
        self.assertEqual(highlighted(report_html.sens_html(sn, out)), report_html.usd(d["target"]))


class SensitivityGridCentresOnTheTicker(unittest.TestCase):
    """#22: the Gordon grid used META's ROIC (20-30%) and margin (34-38%) for every ticker and highlighted the
    (25%, 36%) cell as the base case; the bridge's year labels were META's (FY+3 … FY+14, NOPAT 2041, 2040)."""

    def inputs(self):
        inp = _synth.engine_inputs(roic=(0.18, 0.22, 0.26))
        inp["scenarios"]["base"]["steady_margin"] = 0.40
        inp["blend"]["convergence_years"] = 6
        return inp

    def test_the_highlighted_cell_is_the_base_dcf(self):
        inp = self.inputs()
        out = mm.Model(inp).run()
        sn = report_html.sensitivities(inp)
        self.assertIn(0.22, sn["roics"])
        self.assertIn(0.40, sn["margins"])
        html = report_html.sens_html(sn, out)
        self.assertEqual(highlighted(html), report_html.usd(out["scenarios"]["base"]["dcf"]["target"]))
        self.assertIn("6-year reinvestment glide", html)

    def test_the_bridge_names_this_model_s_years(self):
        inp = self.inputs()
        out = mm.Model(inp).run()
        bridge = report_html.bridge_table(out["scenarios"]["base"], out["wacc"], inp["scenarios"]["base"], out["price"], "Base", inp["blend"])
        self.assertIn("through FY2028", bridge)
        self.assertIn("(FY2029 … FY2034)", bridge)
        self.assertIn("NOPAT FY2035", bridge)
        self.assertIn("EV / EBITDA (FY2034)", bridge)
        self.assertNotIn("FY+14", bridge)


if __name__ == "__main__":
    unittest.main()
