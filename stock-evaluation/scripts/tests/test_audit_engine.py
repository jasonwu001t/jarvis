"""Engine and report faults of the 2026-10-26 bug audit (#91, #255, #256) on synthetic
inputs. Run with `python3 -B -m unittest discover -s scripts/tests` from the skill root."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _synth  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
