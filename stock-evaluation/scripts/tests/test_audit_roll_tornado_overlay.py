"""Faults of the 2026-10-26 bug audit in rolling a quarter, the tornado's break-evens and the backtest's overlay gate
(#88, #96, #257), on synthetic companies. Run with `python3 -B -m unittest discover -s scripts/tests` from the skill root."""
import contextlib
import datetime as dt
import io
import json
import math
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _synth  # noqa: E402
import backtest  # noqa: E402
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


class OverlayGateReadsWhatWasPublished(unittest.TestCase):
    """#257: the backtest's regime gate read NFCI at today's vintage keyed by observation date, so a Monday decision
    gated on the Friday print released the next Wednesday, at its revised value."""

    # (observation date, value, published): the 2026-10-09 print is revised and the 2026-10-16 one released on 10-21
    NFCI = [("2026-10-02", -0.52, "2026-10-07"), ("2026-10-09", -0.499, "2026-10-14"),
            ("2026-10-09", -0.44, "2026-10-21"), ("2026-10-16", -0.40, "2026-10-21")]

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dir = os.path.join(self.tmp, "ZZZ")
        os.makedirs(self.dir)
        tmpl = _synth.engine_inputs()
        tmpl["blend"]["overlays"] = {"regime": {"nfci_max": -0.45}}
        with open(os.path.join(self.dir, "inputs.json"), "w", encoding="utf-8") as fh:
            json.dump(tmpl, fh)
        world = _synth.AtlasWorld(latest=(2026, 3))
        self.kpis = []
        for kid, series in world.kpis.items():
            scale = 1.0 if kid in backtest.PER_SHARE else 1e6
            pts = lambda annual: [{"period": f"FY{k // 10}" if annual else f"{k // 10}-Q{k % 10}", "end": r["end"],
                                   "kind": "annual" if annual else "quarterly", "value": r["value"] * scale, "filed": r["end"]}
                                  for k, r in series.items() if (k % 10 == 0) == annual]
            self.kpis.append({"id": kid, "quarterly": pts(False), "annual": pts(True)})
        days, d = [], dt.date(2024, 9, 2)
        while d <= dt.date(2026, 10, 23):
            if d.weekday() < 5:
                days.append(d.isoformat())
            d += dt.timedelta(days=1)
        self.prices = {"ZZZ": {x: 100 * math.exp(0.0004 * i + 0.01 * math.sin(i / 3)) for i, x in enumerate(days)},
                       "SPY": {x: 400 * math.exp(0.0003 * i + 0.008 * math.sin(i / 3 + 0.5)) for i, x in enumerate(days)}}
        self._saved = backtest.get, backtest.guid.collect
        backtest.get, backtest.guid.collect = self.get, lambda *a, **kw: []

    def tearDown(self):
        backtest.get, backtest.guid.collect = self._saved
        shutil.rmtree(self.tmp)

    def get(self, path, **params):
        rows = lambda pairs: {"data": {"rows": [{"as_of_date": a, "value": v} for a, v in pairs]}}
        if path == "/api/v1/macro/series/NFCI":
            cutoff, vintage = (params.get("as_of") or "9999")[:10], {}
            for obs, v, published in self.NFCI:
                if published <= cutoff:
                    vintage[obs] = v
            return rows(sorted(vintage.items(), reverse=True))
        if path.startswith("/api/v1/macro/series/"):
            return rows([("2026-10-15", {"VIXCLS": 15.0, "BAA10Y": 1.5, "DGS10": 4.0}[path.rsplit("/", 1)[1]])])
        if path.startswith("/api/v1/market/prices/"):
            px = self.prices[path.rsplit("/", 1)[1]]
            return {"data": {"rows": [{"as_of_date": x, "close": px[x]} for x in sorted(px, reverse=True)]}}
        if path.startswith("/api/v1/filings/ticker/"):
            return {"data": {"xbrl": {"kpis": self.kpis}}}
        if path.endswith("sec.earnings_releases/rows"):
            return {"data": {"rows": [{"filing_date": "2026-10-15", "form": "8-K"}]}}
        if path.endswith("sec.company_facts/rows"):
            return {"data": {"rows": []}}
        raise AssertionError(f"unexpected atlas call {path} {params}")

    def test_a_monday_decision_gates_on_the_print_published_by_then(self):
        out = os.path.join(self.tmp, "bt")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            backtest.main(["--dir", self.dir, "--since", "2026-01-01", "--out", out])
        with open(os.path.join(out, "results.json"), encoding="utf-8") as fh:
            pts = json.load(fh)["results"]["guidance_ev_overlays"]["points"]
        self.assertEqual(pts[0]["date"], "2026-10-19")                          # release Thursday + 2 trading days
        self.assertEqual(pts[0]["overlay"]["stress"], [])                       # 2026-10-09 first print -0.499, not 10-16's -0.40
        self.assertEqual(pts[0]["overlay"]["regime_cap"], 1.0)


if __name__ == "__main__":
    unittest.main()
