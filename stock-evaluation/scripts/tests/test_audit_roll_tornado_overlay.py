"""Faults of the 2026-10-26 bug audit in rolling a quarter and the tornado's break-evens (#88, #96), on synthetic
companies. Run with `python3 -B -m unittest discover -s scripts/tests` from the skill root."""
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
import monitor  # noqa: E402
import thesis_tracker as tt  # noqa: E402
import valuation_engine as mm  # noqa: E402


def _extend_consensus(inp, keys=(20272, 20273, 20274, 20290)):
    """Consensus for FY2027's open quarters and FY2029 (a FY2026 Q4 folder): each line copied from a year earlier."""
    for line, vals in inp["lines"].items():
        for k in keys:
            if str(k - 10) in vals:
                vals[str(k)] = vals[str(k - 10)]


def _offline():
    def refuse(path, **params):
        raise RuntimeError(f"offline test: {path}")
    return refuse


class ApplyActualsAcrossAFiscalYear(unittest.TestCase):
    """#88: --apply-actuals of FY+1 Q1 after a Q4 rolled as_of into a year the consensus did not reach (no new FY+2):
    the engine divided by zero, main() had already saved that inputs.json, and the quarter was never added to periods."""

    def roll(self, inp, world):
        new = monitor.detect_new_quarters(inp, world.kpis)
        return new, monitor.apply_actuals(inp, world.kpis, new, {})

    def test_without_the_new_horizon_as_of_holds_with_a_note(self):
        inp = _synth.engine_inputs(fy=2026, q=4)
        new, notes = self.roll(inp, _synth.AtlasWorld(latest=(2027, 1)))
        self.assertEqual(new, [20271])
        mm.Model(inp).run()
        self.assertEqual((inp["as_of"]["latest_reported_fy"], inp["as_of"]["latest_reported_q"]), (2026, 4))
        self.assertIn("20271", inp["lines"]["revenue"])                        # the actuals are written all the same
        self.assertTrue(any("not rolled" in n and "20290" in n for n in notes), notes)

    def test_with_the_consensus_extended_the_quarter_rolls_into_periods(self):
        inp = _synth.engine_inputs(fy=2026, q=4)
        _extend_consensus(inp)
        self.roll(inp, _synth.AtlasWorld(latest=(2027, 1)))
        a = inp["as_of"]
        self.assertEqual((a["latest_reported_fy"], a["latest_reported_q"], a["balance_sheet_date"]), (2027, 1, "2027-03-31"))
        status = {p["key"]: p["status"] for p in inp["periods"]}
        self.assertEqual(status.get(20271), "actual")
        self.assertEqual([status.get(k) for k in (20272, 20273, 20274, 20290)], ["consensus"] * 4)
        keys = [p["key"] for p in inp["periods"]]
        self.assertLess(keys.index(20264), keys.index(20271))
        self.assertLess(keys.index(20274), keys.index(20270))                 # time order: a year after its quarters
        mm.Model(inp).run()

    def test_the_engine_names_a_missing_year(self):
        inp = _synth.engine_inputs(fy=2026, q=4)
        inp["as_of"].update(latest_reported_fy=2027, latest_reported_q=1)
        with self.assertRaisesRegex(ValueError, "FY2029"):
            mm.Model(inp)


class MonitorWritesOnlyARunnableRoll(unittest.TestCase):
    """#88: monitor.py --apply-actuals wrote inputs.json before running the model, so a roll the engine could not run
    was saved and every later run crashed until someone repaired the file by hand."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._saved = (monitor.HERE, monitor.get, monitor.atlas_data.get, monitor.live_fundamentals, monitor.live_guidance)
        monitor.HERE, monitor.get, monitor.atlas_data.get = self.tmp, _offline(), _offline()
        monitor.live_guidance = lambda inputs, folder: {}

    def tearDown(self):
        monitor.HERE, monitor.get, monitor.atlas_data.get, monitor.live_fundamentals, monitor.live_guidance = self._saved
        shutil.rmtree(self.tmp)

    def run_monitor(self, inp, world):
        path = os.path.join(self.tmp, "inputs.json")
        inp["wacc"].update(beta_mode="manual", risk_free_mode="manual")       # no live beta or ten-year to fetch
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(inp, fh)
        monitor.live_fundamentals = world.fundamentals
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            monitor.main(["--dir", self.tmp, "--apply-actuals"])
        with open(path, encoding="utf-8") as fh:
            return json.load(fh), out.getvalue()

    def test_the_saved_inputs_run(self):
        saved, _ = self.run_monitor(_synth.engine_inputs(fy=2026, q=4), _synth.AtlasWorld(latest=(2027, 1)))
        mm.Model(saved).run()

    def test_a_roll_the_engine_cannot_run_is_not_saved(self):
        inp = _synth.engine_inputs(fy=2026, q=4)
        _extend_consensus(inp)
        world = _synth.AtlasWorld(latest=(2027, 1))
        del world.kpis["shares_diluted"][20271]                               # a filer that tags no share count for the quarter
        saved, report = self.run_monitor(inp, world)
        self.assertEqual((saved["as_of"]["latest_reported_fy"], saved["as_of"]["latest_reported_q"]), (2026, 4))
        self.assertNotIn("20271", saved["lines"]["revenue"])
        self.assertIn("inputs.json left as it was", report)


class TornadoBracketsAboveTerminalGrowth(unittest.TestCase):
    """#96: the beta and ten-year break-evens were bracketed across WACC <= terminal growth, where the Gordon value flips
    sign: a low-beta name read 'not reachable' although a break-even lay in range, or printed the pole (WACC = g)."""

    def setUp(self):
        self.inp = _synth.engine_inputs()
        self.inp["wacc"]["beta"] = 0.529                                        # a low beta (MCD's), terminal growth 3%
        for s in self.inp["scenarios"].values():
            s["terminal_growth"] = 0.03

    def house(self, name, x):
        return tt._targets(tt._perturb(self.inp, name, x))["house"]

    def test_a_break_even_in_range_is_found(self):
        price = tt._targets(self.inp)["house"] * 0.8
        rows = {r["name"]: r for r in tt.assumption_impact(self.inp, price)}
        for name in ("beta", "risk_free"):
            be = rows[name]["break_even"]
            self.assertIsNotNone(be, name)
            self.assertGreater(be, 0, name)
            self.assertAlmostEqual(self.house(name, be), price, delta=0.005 * price)

    def test_no_break_even_is_not_reachable_rather_than_the_pole(self):
        rows = {r["name"]: r for r in tt.assumption_impact(self.inp, 150.0)}
        for name in ("beta", "risk_free"):
            self.assertIsNone(rows[name]["break_even"], rows[name]["break_even_label"])
            self.assertEqual(rows[name]["break_even_label"], "not reachable in the solve range")

    def test_terminal_growth_stays_below_wacc_in_every_scenario(self):
        self.inp["scenarios"]["bull"]["terminal_growth"] = 0.05                 # 2pp above the base case's
        self.inp["blend"]["target_position"] = 0.5
        rows = {r["name"]: r for r in tt.assumption_impact(self.inp, 600.0)}
        be = rows["terminal_growth"]["break_even"]
        self.assertIsNotNone(be)
        self.assertAlmostEqual(self.house("terminal_growth", be), 600.0, delta=3.0)

    def test_solve_rejects_a_pole(self):
        self.assertIsNone(tt._solve(lambda x: 1 / x, 0.5, -1.0, 1.5))           # the only sign change is the pole at 0
        self.assertAlmostEqual(tt._solve(lambda x: 1 / x, 0.5, 1.0, 3.0), 2.0, places=6)


if __name__ == "__main__":
    unittest.main()
