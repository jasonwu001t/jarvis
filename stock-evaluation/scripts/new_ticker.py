"""Scaffold a ticker folder for the stock-evaluation skill.

  python3 new_ticker.py NVDA "NVIDIA Corporation" --dir ~/AlphaResearch/research/NVDA [--fye 1]

Writes <dir>/inputs.json with every key the engine reads, placeholder scenario assumptions and an
empty consensus block, plus <dir>/reports/. Fill `lines` and `periods` from SEC XBRL (atlas) and the
consensus block by hand; see ../references/inputs-schema.md and ../references/data-sources.md.
"""
from __future__ import annotations

import json
import os
import sys


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        return 2
    ticker, name = args[0].upper(), args[1]
    out_dir = argv[argv.index("--dir") + 1] if "--dir" in argv else os.path.join(os.getcwd(), ticker)
    fye = int(argv[argv.index("--fye") + 1]) if "--fye" in argv else 12
    os.makedirs(os.path.join(out_dir, "reports"), exist_ok=True)
    path = os.path.join(out_dir, "inputs.json")
    if os.path.exists(path):
        print(f"refusing to overwrite {path}")
        return 1
    scn = lambda roic, mg, mult: {"terminal_growth": 0.035, "steady_roic": roic, "steady_margin": mg, "steady_tax": 0.15, "target_multiple": mult}
    inputs = {
        "company": {"ticker": ticker, "name": name, "currency": "USD", "fiscal_year_end_month": fye},
        "as_of": {"latest_reported_fy": None, "latest_reported_q": None, "balance_sheet_date": None,
                  "consensus_date": None, "consensus_source": "FILL: where the consensus block came from",
                  "method_source": "stock-evaluation skill: three-scenario DCF + P/E (美投估值模板 method)"},
        "market": {"price": None, "price_date": None, "fx": 1.0, "adr_ratio": 1.0, "market_cap_musd_override": None},
        "wacc": {"beta": None, "risk_free": None, "erp": 0.042, "pretax_cost_of_debt": None,
                 "risk_free_mode": "dgs10", "beta_mode": "adjusted_2y_weekly",
                 "_note": "beta and risk_free are refreshed live by monitor.py when the modes say so; pretax cost of debt from interest expense / debt"},
        "scenarios": {"bear": scn(0.15, 0.25, 15), "base": scn(0.20, 0.28, 18), "bull": scn(0.25, 0.30, 20),
                      "_note": "FILL from the company's own ROIC, margin and multiple history"},
        "blend": {"dcf_weight": 0.5, "target_position": 0.0, "multiple_type": "P/E", "earnings_basis": "GAAP", "convergence_years": 12},
        "rating": {"label": "FILL"},
        "thesis": {"summary": "FILL: one paragraph, what the house believes that consensus does not", "source": ""},
        "adjustments": [],
        "reference_multiples": {"current_fwd_pe": None, "pe5y_low": None, "pe5y_avg": None, "pe5y_high": None,
                                "_note": "own 5-year forward multiple range; vendor data, keyed in"},
        "segments": {},
        "periods": [],
        "lines": {k: {} for k in ["revenue", "operating_income", "pretax_income", "income_tax", "net_income", "adjustments",
                                  "adjusted_net_income", "diluted_shares", "dps", "dividends_total", "buybacks", "d_and_a", "sbc",
                                  "wc_increase", "operating_cash_flow", "capex", "finance_lease_additions", "nopat", "fcff",
                                  "cash_and_st_investments", "debt", "investments", "minority_interest", "equity", "other_income"]},
        "baseline": {},
        "monitor": {"rules": [
            {"name": "Below bear case", "when": "price <= bear_target", "action": "Price at or under the bear-case value: re-underwrite the thesis lines; cut if they are not tracking."},
            {"name": "Add zone", "when": "house_upside >= 0.20", "action": "House target implies >= 20% upside: add toward full size if the next print confirms the thesis."},
            {"name": "Hold zone", "when": "0.05 <= house_upside < 0.20", "action": "Upside between 5% and 20%: hold; no action."},
            {"name": "At target", "when": "house_upside < 0.05", "action": "Less than 5% to the house target: trim, or raise the target only with new evidence."},
            {"name": "Multiple above own 5y high", "when": "pe5y_high is not None and price_implied_pe_base > pe5y_high", "action": "Price-implied forward multiple above the own 5-year high: favor trimming."}]},
        "_units": "USD millions unless per-share; rates as fractions; period keys year*10+quarter (0 = fiscal year)",
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(inputs, fh, indent=1, ensure_ascii=False)
    print(f"wrote {path}; now fill periods, lines (actuals from atlas XBRL + the consensus block), segments, adjustments, scenarios")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
