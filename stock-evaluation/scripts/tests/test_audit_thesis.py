"""Thesis-tracker faults of the 2026-10-26 bug audit (#97, #98) on synthetic inputs."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _synth  # noqa: E402
import digest  # noqa: E402
import thesis_tracker as tt  # noqa: E402
import valuation_engine as mm  # noqa: E402

TODAY = dt.date(2026, 10, 31)


def _claims(inp, *claims, live=None, targets=None):
    inp = dict(inp, thesis={"claims": list(claims)})
    out = mm.Model(inp).run()
    return {c["id"]: c for c in tt.evaluate_claims(inp, inp, out, TODAY, [], live or {}, targets)}


class NearMissMeasuresTheViolatedBound(unittest.TestCase):
    """#97: a two-sided band read a value far above max as near its min (and far below min as near its max)."""

    def test_the_helper(self):
        self.assertFalse(tt.near_miss(0.05, 0.0, 0.10, 0.5))           # in range: no miss at all
        self.assertFalse(tt.near_miss(0.50, 0.0, 0.10, 0.5))           # far above max: broken
        self.assertFalse(tt.near_miss(-0.60, 0.0, 0.10, 0.5))          # far below a zero min: broken
        self.assertTrue(tt.near_miss(0.12, 0.0, 0.10, 0.5))            # just above max: watch
        self.assertTrue(tt.near_miss(-0.11, -0.10, None, 0.5))         # a negative min, just below: watch
        self.assertFalse(tt.near_miss(-0.20, -0.10, None, 0.5))

    def test_consensus_revision_far_out_of_a_band_is_broken(self):
        live = {"consensus": {"next": {"change": {"pct": 0.60, "days": 30, "from": 1.0, "to": 1.6},
                                       "latest": {"eps_forecast": 1.6, "estimates": 10}, "report_date": "2026-11-20"}}}
        got = _claims(_synth.engine_inputs(), {"id": "c", "check": {"kind": "consensus_revision", "min": -0.05,
                                                                   "max": 0.10, "tolerance": 0.5}}, live=live)
        self.assertEqual(got["c"]["status"], "broken")

    def test_target_vs_model_far_out_of_a_band_is_broken(self):
        targets = {"metrics": {"om": {"min": 0.01, "max": 0.02}}, "source": {"title": "t", "published": "2026-01-01"}}
        got = _claims(_synth.engine_inputs(), {"id": "t", "check": {"kind": "target_vs_model", "target": "om",
                                                                   "model": "q5_q8_operating_margin"}},
                      targets=targets)
        self.assertEqual(got["t"]["status"], "broken")


class TargetBasisAndUnit(unittest.TestCase):
    """#259: a non-GAAP margin target was scored against the GAAP model margin, and a value was shown as percent
    whenever it was below 3 (a $2.50 EPS target as 250%)."""

    def _one(self, metric, model):
        targets = {"metrics": {"t": metric}, "source": {"title": "t", "published": "2026-01-01"}}
        return _claims(_synth.engine_inputs(), {"id": "x", "check": {"kind": "target_vs_model", "target": "t",
                                                                    "model": model}}, targets=targets)["x"]

    def test_a_non_gaap_margin_target_is_not_scored_against_the_gaap_margin(self):
        got = self._one({"min": 0.01, "max": 0.02, "basis": "non_gaap", "unit": "pct"}, "q5_q8_operating_margin")
        self.assertEqual(got["status"], "review")
        self.assertIn("not compared", got["metric"])

    def test_an_eps_target_is_dollars(self):
        got = self._one({"min": 2.50, "unit": "usd"}, "q5_q8_eps")
        self.assertNotIn("250", got["metric"])
        self.assertIn("2.50", got["metric"])


class StatusVocabulary(unittest.TestCase):
    """#98: MCD's 'fail'/'pass' statuses counted as pending, so failed claims never showed as broken."""

    def test_aliases_and_unknown_statuses(self):
        self.assertEqual(tt.normalise_status("fail"), ("broken", None))
        self.assertEqual(tt.normalise_status("pass"), ("on_track", None))
        st, note = tt.normalise_status("maybe")
        self.assertEqual(st, "review")
        self.assertIn("unknown status 'maybe'", note)

    def test_manual_and_rule_claims_and_the_digest(self):
        got = _claims(_synth.engine_inputs(), {"id": "m", "status": "fail"},
                      {"id": "r", "check": {"kind": "rule", "name": "never", "when_clear": "pass"}})
        self.assertEqual((got["m"]["status"], got["r"]["status"]), ("broken", "on_track"))
        self.assertEqual(digest.claim_counts({"claims": {"a": "fail", "b": "pass", "c": "weird"}}),
                         {"on_track": 1, "watch": 0, "broken": 1, "review": 1, "pending": 0})


if __name__ == "__main__":
    unittest.main()
