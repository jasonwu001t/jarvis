"""#143: atlas_data.fundamentals trusted the payload's top-level currency, so figures atlas left native (no FX
series for DKK, or DEXTAUS not stored) would be read as USD millions."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import atlas_data  # noqa: E402


def _payload(unit, note=None):
    return {"data": {"currency": "USD", "native_unit": "DKK", "per_share_divisor": 1.0,
                     "fx": {"note": note} if note else {"series": "DEXDKUS"},
                     "kpis": [{"id": "revenue", "unit": unit, "quarterly": [
                         {"period": "2026-Q2", "end": "2026-06-30", "value": 5e9}], "annual": []},
                              {"id": "eps_diluted", "unit": f"{unit}/share", "quarterly": [
                                  {"period": "2026-Q2", "end": "2026-06-30", "value": 1.5}], "annual": []}]}}


class CurrencyGuard(unittest.TestCase):
    def setUp(self):
        self.saved = atlas_data.get

    def tearDown(self):
        atlas_data.get = self.saved

    def test_native_figures_are_refused_not_read_as_dollars(self):
        atlas_data.get = lambda path, **kw: _payload("DKK", "no FX series for DKK; values stay in DKK")
        with self.assertRaises(atlas_data.NotConverted) as caught:
            atlas_data.fundamentals("ZZZ", currency="USD")
        self.assertIn("no FX series for DKK", str(caught.exception))

    def test_converted_figures_read_as_before(self):
        atlas_data.get = lambda path, **kw: _payload("USD")
        out = atlas_data.fundamentals("ZZZ", currency="USD")
        self.assertEqual(out["kpis"]["revenue"][20262]["value"], 5000.0)


if __name__ == "__main__":
    unittest.main()
