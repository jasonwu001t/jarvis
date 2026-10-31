"""Synthetic companies for the skill's tests: an engine-ready inputs.json and a fake atlas for fill_from_atlas.py.

engine_inputs(): actual quarters FY-3 Q1 … FY Qq plus their fiscal years, the consensus for the rest of FY, FY+1 and FY+2;
revenue flat within a year, every flow a fixed share of revenue. AtlasWorld: the KPI series, company-facts rows and
guidance releases fill_from_atlas.py reads, served by monkeypatching its atlas calls."""
from __future__ import annotations

import datetime as dt


def _scn(roic, margin, mult, prob):
    return {"terminal_growth": 0.035, "steady_roic": roic, "steady_margin": margin, "steady_tax": 0.15,
            "target_multiple": mult, "probability": prob}


def engine_inputs(fy=2026, q=2, growth=0.10, year_growth=None, margin=0.30, fc_margin=None, wc_share=0.02,
                  capex_share=0.06, da_share=0.05, cost_of_debt=0.045, segments=None, roic=(0.12, 0.20, 0.25)):
    year_growth = year_growth or {}
    fc_margin = margin if fc_margin is None else fc_margin
    first = fy - 3
    A = {first: 4000.0}
    for y in range(first + 1, fy + 3):
        A[y] = A[y - 1] * (1 + year_growth.get(y, growth))
    L = {}

    def put(line, k, v):
        L.setdefault(line, {})[str(k)] = v

    def flows(k, rev, mg):
        oi = rev * mg
        pre = oi
        tax = pre * 0.15
        ni = pre - tax
        vals = {"revenue": rev, "operating_income": oi, "other_income": 0.0, "pretax_income": pre, "income_tax": tax,
                "net_income": ni, "adjustments": 0.0, "adjusted_net_income": ni, "dps": 0.0, "dividends_total": 0.0,
                "buybacks": 0.0, "d_and_a": rev * da_share, "sbc": rev * 0.03, "wc_increase": rev * wc_share,
                "capex": rev * capex_share, "finance_lease_additions": 0.0, "gross_profit": rev * 0.6,
                "operating_cash_flow": oi * 0.85 + rev * (da_share + 0.03 - wc_share)}
        for line, v in vals.items():
            put(line, k, v)
        put("diluted_shares", k, 100.0)
        for name, share in (segments or {}).items():
            put(f"seg:{name}", k, rev * share)
            put(f"segoi:{name}", k, oi * share)

    def balance(k, y):
        for line, v in (("cash_and_st_investments", 2000.0), ("debt", 500.0), ("investments", 0.0), ("minority_interest", 0.0),
                        ("equity", 6000.0 * A[y] / A[first])):
            put(line, k, v)

    periods = []
    for y in range(first, fy + 1):
        for i in range(1, 5):
            k = y * 10 + i
            actual = y < fy or i <= q
            flows(k, A[y] / 4, margin if actual else fc_margin)
            balance(k, y)
            periods.append({"key": k, "year": y, "q": i, "status": "actual" if actual else "consensus"})
        k = y * 10
        for line in list(L):
            if all(str(y * 10 + i) in L[line] for i in range(1, 5)) and line not in ("diluted_shares",):
                vals = [L[line][str(y * 10 + i)] for i in range(1, 5)]
                put(line, k, vals[-1] if line in ("cash_and_st_investments", "debt", "investments", "minority_interest", "equity") else sum(vals))
        put("diluted_shares", k, 100.0)
        periods.append({"key": k, "year": y, "q": 0, "status": "actual" if (y < fy or q == 4) else "consensus"})
    for y in (fy + 1, fy + 2):
        flows(y * 10, A[y], fc_margin)
        balance(y * 10, fy)
        periods.append({"key": y * 10, "year": y, "q": 0, "status": "consensus"})
    seg_block = {name: {"parent": None, "oi_line": f"segoi:{name}"} for name in (segments or {})}
    return {
        "company": {"ticker": "ZZZ", "name": "Synthetic Co", "currency": "USD", "fiscal_year_end_month": 12},
        "as_of": {"latest_reported_fy": fy, "latest_reported_q": q, "balance_sheet_date": f"{fy}-{3 * q:02d}-{30 if q in (2, 3) else 31}",
                  "consensus_date": f"{fy}-08-01", "consensus_source": "synthetic"},
        "market": {"price": 300.0, "price_date": f"{fy}-10-23", "fx": 1.0, "adr_ratio": 1.0, "market_cap_musd_override": None},
        "wacc": {"beta": 1.0, "risk_free": 0.04, "erp": 0.05, "pretax_cost_of_debt": cost_of_debt},
        "scenarios": {"bear": _scn(roic[0], 0.25, 15, 0.25), "base": _scn(roic[1], 0.30, 20, 0.5), "bull": _scn(roic[2], 0.33, 25, 0.25)},
        "blend": {"dcf_weight": 0.5, "target_position": 0.0, "multiple_type": "P/E", "earnings_basis": "GAAP", "convergence_years": 12},
        "rating": {"label": "test"}, "thesis": {"summary": "test", "claims": []}, "adjustments": [],
        "reference_multiples": {"current_fwd_pe": 20.0, "pe5y_low": 15.0, "pe5y_avg": 20.0, "pe5y_high": 25.0},
        "segments": seg_block, "periods": periods, "lines": L, "baseline": {}, "monitor": {"rules": []},
    }


# ------------------------------------------------------------------------------------------------- fake atlas
def quarter_end(y, i):
    return dt.date(y, 3 * i, 30 if i in (2, 3) else 31).isoformat()


class AtlasWorld:
    """KPI series (USD m) for fiscal years 2022 … latest, flat within a year unless `quarter_rev` says otherwise.

    wc_share(y, i) sets each quarter's working-capital build as a share of revenue (the fill derives it back as
    NOPAT + D&A + SBC − OCF); interest_income / interest_expense are per quarter, USD m."""

    def __init__(self, latest=(2026, 2), quarter_rev=None, wc_share=None, margin=0.30, cash=4000.0, debt=1000.0,
                 interest_income=40.0, interest_expense=10.0, releases=None):
        self.latest = latest
        self.quarter_rev = quarter_rev or (lambda y, i: 1000.0 * 1.1 ** (y - 2022))
        self.wc_share = wc_share or (lambda y, i: 0.02)
        self.margin, self.cash, self.debt = margin, cash, debt
        self.interest_income, self.interest_expense = interest_income, interest_expense
        self.releases = releases or []
        self.kpis = self._kpis()

    def quarters(self):
        fy, q = self.latest
        return [(y, i) for y in range(2022, fy + 1) for i in range(1, 5) if (y, i) <= (fy, q)]

    def _kpis(self):
        K = {}

        def put(kpi, k, v, end):
            K.setdefault(kpi, {})[k] = {"value": v, "end": end}

        for y, i in self.quarters():
            k, end = y * 10 + i, quarter_end(y, i)
            rev = self.quarter_rev(y, i)
            oi = rev * self.margin
            pre = oi + self.interest_income - self.interest_expense
            tax = pre * 0.15
            da, sbc = rev * 0.05, rev * 0.03
            ocf = oi * 0.85 + da + sbc - rev * self.wc_share(y, i)
            for kpi, v in (("revenue", rev), ("operating_income", oi), ("pretax_income", pre), ("income_tax_expense", tax),
                           ("net_income", pre - tax), ("shares_diluted", 100.0), ("dividends_per_share", 0.0), ("dividends_paid", 0.0),
                           ("buybacks", 0.0), ("depreciation_amortization", da), ("share_comp", sbc), ("operating_cash_flow", ocf),
                           ("capex", rev * 0.06), ("finance_lease_additions", 0.0), ("gross_profit", rev * 0.6),
                           ("eps_diluted", (pre - tax) / 100.0), ("interest_expense", self.interest_expense)):
                put(kpi, k, v, end)
            for kpi, v in (("cash", self.cash), ("total_debt", self.debt), ("equity", 8000.0)):
                put(kpi, k, v, end)
        fy, q = self.latest
        for y in range(2022, fy + 1):
            if (y, 4) > (fy, q):
                continue
            end = quarter_end(y, 4)
            for kpi in list(K):
                qv = [K[kpi][y * 10 + i]["value"] for i in range(1, 5)]
                v = qv[-1] if kpi in ("cash", "total_debt", "equity") else (qv[0] if kpi == "shares_diluted" else sum(qv))
                if kpi == "eps_diluted":
                    v = sum(qv)
                put(kpi, y * 10, v, end)
        return K

    def fundamentals(self, ticker, currency="USD"):
        return {"kpis": self.kpis, "company_type": "default", "per_share_divisor": 1.0, "native_unit": "USD"}

    def facts_rows(self, metric):
        """sec.company_facts rows: InvestmentIncomeInterest as 3-month durations for Q1-Q3 and the fiscal year (no Q4 row)."""
        if metric != "InvestmentIncomeInterest":
            return []
        rows = []
        fy, q = self.latest
        for y, i in self.quarters():
            if i < 4:
                start = (dt.date.fromisoformat(quarter_end(y, i)) - dt.timedelta(days=90)).isoformat()
                rows.append({"metric": metric, "value": self.interest_income * 1e6, "period_start": start, "period_end": quarter_end(y, i)})
            if i == 4:
                rows.append({"metric": metric, "value": 4 * self.interest_income * 1e6, "period_start": f"{y}-01-01", "period_end": quarter_end(y, 4)})
        return rows

    def get(self, path, **params):
        if path.startswith("/api/v1/market/prices/"):
            return {"data": {"rows": [{"close": 100.0, "as_of_date": "2026-10-23"}]}}
        if path.endswith("sec.company_facts/rows"):
            return {"data": {"rows": self.facts_rows(params.get("eq.metric"))}}
        raise AssertionError(f"unexpected atlas call {path} {params}")
