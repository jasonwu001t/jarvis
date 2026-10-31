"""The equity bridge's balance-sheet lines (cash and short-term investments, debt, investments) as the 2026-10-26 bug
audit found them in the skill (#20, #21, #251), each on synthetic data. Run with
`python3 -B -m unittest discover -s scripts/tests` from the skill root."""
import contextlib
import datetime as dt
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
import monitor  # noqa: E402
import valuation_engine as mm  # noqa: E402
from test_onboarding_faults import FillCase  # noqa: E402


class ApplyActualsBridge(unittest.TestCase):
    """#20: --apply-actuals wrote cash only where MarketableSecuritiesCurrent was stated at the date and investments
    only where both default concepts were, then rolled as_of anyway: the bridge read the consensus value the model
    carried for the quarter (or 0) and nothing said so."""

    def setUp(self):
        self.inp = _synth.engine_inputs(fy=2026, q=2)         # 2000 of cash in every period, the 20263 consensus too
        self.saved_get = monitor.get

    def tearDown(self):
        monitor.get = self.saved_get

    def apply(self, world, extras=None):
        keys = monitor.detect_new_quarters(self.inp, world.kpis)
        self.assertEqual(keys, [20263])
        if extras is None:
            monitor.get = world.get
            extras = {20263: monitor.live_balance_sheet_extras("ZZZ", world.kpis["revenue"][20263]["end"])}
        return monitor.apply_actuals(self.inp, world.kpis, keys, extras)

    def line(self, name):
        return self.inp["lines"][name].get("20263")

    def test_cash_kpi_without_securities_facts(self):
        notes = self.apply(_synth.AtlasWorld(latest=(2026, 3), cash=4000.0), {20263: {}})
        self.assertEqual(self.line("cash_and_st_investments"), 4000.0)        # the cash KPI, not the 2000 consensus
        self.assertTrue(any(n.startswith("WARNING") and "cash_and_st_investments" in n for n in notes), notes)

    def test_securities_at_the_date_debt_with_current_portion_and_10k_balances(self):
        world = _synth.AtlasWorld(latest=(2026, 3), cash=4000.0, debt=1000.0,
                                  balances={"long_term_debt_incl_current": lambda y, i: 1300.0},
                                  facts={"MarketableSecuritiesCurrent": {"2025-12-31": 700.0},   # no longer tagged
                                         "DebtSecuritiesCurrent": {"2026-09-30": 2500.0},        # the concept it moved to
                                         "EquityMethodInvestments": {"2025-12-31": 300.0},       # 10-K only
                                         "FinanceLeaseLiability": {"2025-12-31": 50.0}})
        self.apply(world)
        self.assertEqual(self.line("cash_and_st_investments"), 6500.0)        # 4000 + 2500 stated at 2026-09-30
        self.assertEqual(self.line("debt"), 1350.0)                           # incl. the current portion, + leases
        self.assertEqual(self.line("investments"), 300.0)                     # the 10-K balance, nine months old

    def test_composite_kpi_and_the_folder_investment_mapping(self):
        world = _synth.AtlasWorld(latest=(2026, 3), cash=4000.0,
                                  balances={"cash_and_short_term_investments": lambda y, i: 9000.0})
        self.inp["balance_mapping"] = {"investment_concepts": ["EquityMethodInvestments", "OtherLongTermInvestments"]}
        ex = {"EquityMethodInvestments": {"value": 300.0, "end": "2026-09-30"},
              "OtherLongTermInvestments": {"value": 200.0, "end": "2026-09-30"}}
        self.apply(world, {20263: ex})
        self.assertEqual(self.line("cash_and_st_investments"), 9000.0)
        self.assertEqual(self.line("investments"), 500.0)

    def test_nothing_stated_carries_the_prior_quarter_and_warns(self):
        world = _synth.AtlasWorld(latest=(2026, 3), cash=4000.0)
        del world.kpis["cash"][20263]
        self.inp["lines"]["cash_and_st_investments"]["20262"] = 2500.0
        notes = self.apply(world, {20263: {}})
        self.assertEqual(self.line("cash_and_st_investments"), 2500.0)        # 20262's actual, not the 2000 consensus
        self.assertTrue(any(n.startswith("WARNING") and "carried from 20262" in n for n in notes), notes)


class ApplyActualsReport(unittest.TestCase):
    """#20: the monitor's warnings now carry what --apply-actuals could not state (main() run offline)."""

    def test_warnings_reach_the_report(self):
        tmp = tempfile.mkdtemp()
        inp = _synth.engine_inputs(fy=2026, q=2)
        inp["wacc"].update(beta_mode="manual", risk_free_mode="manual")
        with open(os.path.join(tmp, "inputs.json"), "w", encoding="utf-8") as fh:
            json.dump(inp, fh)
        world = _synth.AtlasWorld(latest=(2026, 3), cash=4000.0)

        def offline(*a, **kw):
            raise RuntimeError("offline")
        saved = monitor.HERE, monitor.get, monitor.atlas_data.get, monitor.live_kpis
        monitor.HERE, monitor.get, monitor.atlas_data.get, monitor.live_kpis = tmp, offline, offline, lambda t: world.kpis
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                monitor.main(["--apply-actuals"])
            with open(os.path.join(tmp, "reports", f"{dt.date.today().isoformat()}.md"), encoding="utf-8") as fh:
                md = fh.read()
            with open(os.path.join(tmp, "inputs.json"), encoding="utf-8") as fh:
                saved_inputs = json.load(fh)
        finally:
            monitor.HERE, monitor.get, monitor.atlas_data.get, monitor.live_kpis = saved
            shutil.rmtree(tmp)
        self.assertIn("## Warnings", md)
        self.assertIn("cash_and_st_investments", md.split("## Warnings")[1].split("\n## ")[0])
        self.assertEqual(saved_inputs["lines"]["cash_and_st_investments"]["20263"], 4000.0)


class EngineBridgeWarning(unittest.TestCase):
    """#20: with the equity bridge on, a bridge line missing at the latest reported quarter read as 0 silently."""

    def test_missing_line_warns(self):
        inp = _synth.engine_inputs()
        del inp["lines"]["investments"]["20262"]
        out = mm.Model(inp).run()
        self.assertTrue(any("investments" in w and "20262" in w for w in out["warnings"]), out["warnings"])
        inp["blend"]["equity_bridge"] = False
        self.assertFalse([w for w in mm.Model(inp).run()["warnings"] if "investments" in w])


class FillCashAndDebt(FillCase):
    """#21: the fill took cash as the cash KPI plus MarketableSecuritiesCurrent at any earlier date (a concept the filer
    stopped tagging was added forever; ShortTermInvestments and the like were left out) and debt as the noncurrent
    total_debt; a 10-K balance (investments, finance leases) was carried with no age limit."""

    def world(self):
        return _synth.AtlasWorld(latest=(2026, 2), cash=4000.0, debt=1000.0, balances={
            "cash_and_short_term_investments": lambda y, i: 9000.0 if y >= 2025 else None,
            "long_term_debt_incl_current": lambda y, i: 1300.0 if y >= 2024 else None},
            facts={"MarketableSecuritiesCurrent": {"2023-03-31": 700.0},     # last tagged in 2023
                   "DebtSecuritiesCurrent": {"2024-06-30": 2500.0},          # a concept atlas's composite does not read
                   "EquityMethodInvestments": {"2024-12-31": 50.0}})         # one 10-K balance, then no more

    def test_composite_cash_debt_with_current_portion_and_no_stale_carry(self):
        inp = self.fill(self.world())
        L = {line: {int(k): v for k, v in vals.items()} for line, vals in inp["lines"].items()}
        cash = L["cash_and_st_investments"]
        self.assertEqual(cash[20262], 9000.0)          # atlas's cash and short-term investments, not 4000 + a 2023 balance
        self.assertEqual(cash[20231], 4700.0)          # cash plus the concept stated at exactly that date
        self.assertEqual(cash[20242], 6500.0)
        self.assertEqual(cash[20232], 4000.0)          # nothing stated at that date: cash alone, said so
        self.assertEqual(L["debt"][20262], 1300.0)     # long-term debt with its current portion
        self.assertEqual(L["debt"][20231], 1000.0)     # the noncurrent total_debt where nothing else is stated, said so
        self.assertEqual(L["investments"][20254], 50.0)    # the 10-K balance within the year
        self.assertEqual(L["investments"][20262], 0.0)     # not carried forever
        notes = inp["_sources"]["notes"]
        self.assertTrue(any(n.startswith("WARNING") and "cash alone" in n and "20232" in n for n in notes), notes)
        self.assertTrue(any(n.startswith("WARNING") and "total_debt" in n and "20231" in n for n in notes), notes)
        self.assertTrue(any(n.startswith("WARNING") and "EquityMethodInvestments" in n for n in notes), notes)


class BacktestBalanceVintage(unittest.TestCase):
    """#251: the backtest read sec.company_facts at its latest vintage, so a fiscal-year-end balance that a later filing
    repeated looked unknown on the Q4 decision day and the Q3 balance stood in."""

    # (period end, USD m, knowledge time): the year-end balances filed with the 10-K on 2026-01-29, repeated (and
    # recast) in a July filing nobody could read on the decision day
    VINTAGES = {"MarketableSecuritiesCurrent": [("2025-09-30", 300.0, "2025-10-30"), ("2025-12-31", 500.0, "2026-01-29"),
                                                ("2025-12-31", 520.0, "2026-07-30")],
                "EquityMethodInvestments": [("2025-09-30", 60.0, "2025-10-30"), ("2025-12-31", 80.0, "2026-01-29"),
                                            ("2025-12-31", 85.0, "2026-07-30")]}

    def get(self, path, **params):
        if path.startswith("/api/v1/filings/"):
            kpis = {}
            for y in (2023, 2024, 2025):
                for i in range(1, 5):
                    for kid, v in (("revenue", 1000.0), ("operating_income", 300.0), ("pretax_income", 300.0),
                                   ("income_tax_expense", 45.0), ("net_income", 255.0), ("shares_diluted", 100.0),
                                   ("capex", 60.0), ("depreciation_amortization", 50.0), ("share_comp", 30.0),
                                   ("cash", 4000.0), ("total_debt", 1000.0)):
                        kpis.setdefault(kid, {"id": kid, "quarterly": [], "annual": []})["quarterly"].append(
                            {"period": f"{y}-Q{i}", "kind": "quarterly", "end": _synth.quarter_end(y, i), "value": v * 1e6})
            return {"data": {"xbrl": {"kpis": list(kpis.values())}}}
        if path.startswith("/api/v1/market/prices/"):
            days = [dt.date(2025, 12, 1) + dt.timedelta(days=n) for n in range(90)]
            return {"data": {"rows": [{"as_of_date": d.isoformat(), "close": 100.0} for d in reversed(days) if d.weekday() < 5]}}
        if path.startswith("/api/v1/macro/series/"):
            return {"data": {"rows": [{"as_of_date": "2026-01-02", "value": 4.0}]}}
        if path.endswith("sec.earnings_releases/rows"):
            return {"data": {"rows": [{"filing_date": "2026-01-28", "form": "8-K"}]}}
        if path.endswith("sec.company_facts/rows"):
            self.as_of.append(params.get("as_of"))
            best = {}
            for end, v, known in self.VINTAGES.get(params["eq.metric"], []):
                if (params.get("as_of") is None or known < params["as_of"]) and (end not in best or known > best[end][1]):
                    best[end] = (v, known)
            return {"data": {"rows": [{"period_start": None, "period_end": e, "value": v * 1e6, "knowledge_time": f"{k}T21:00:00Z"}
                                      for e, (v, k) in best.items()]}}
        raise AssertionError(f"unexpected atlas call {path} {params}")

    def test_the_q4_decision_reads_the_year_end_balance(self):
        self.as_of = []
        saved = backtest.get, backtest.guid.collect
        backtest.get, backtest.guid.collect = self.get, lambda *a, **kw: []
        try:
            data = backtest.fetch_all("ZZZ", "/nonexistent", "2025-12-01")
            evals = backtest.release_evals("ZZZ", data, "2025-12-01")
        finally:
            backtest.get, backtest.guid.collect = saved
        self.assertEqual(evals, [("2026-01-30", 20254)])          # the release plus two trading days
        inp = backtest.build_inputs(_synth.engine_inputs(fy=2025, q=4), data, 20254, "2026-01-30", "momentum")
        L = inp["lines"]
        self.assertEqual(L["cash_and_st_investments"]["20254"], 4500.0)    # 4000 + the 2025-12-31 securities, not 2025-09-30's
        self.assertEqual(L["investments"]["20254"], 80.0)
        self.assertEqual(set(self.as_of), {"2026-02-13"})                  # read as atlas knew them then (+14 days)


if __name__ == "__main__":
    unittest.main()
