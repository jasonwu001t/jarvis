"""Three-scenario valuation engine (DCF with a linear convergence to steady state + a forward P/E leg).

Ticker-agnostic re-implementation of the 美投估值模板 (Meitou valuation template) v1.37, first built for META.
Pure arithmetic, standard library only. Reads an inputs.json (actual history, sell-side consensus, scenario
assumptions, line-item adjustments) and returns the three-scenario DCF + P/E valuation, the blended target,
the house target and the check list. See ../references/valuation-method.md for the method.

Units: USD millions unless per share; rates are fractions. Period keys are year*10+q
(q = 0 for a fiscal year, 1-4 for a quarter), e.g. 20263 = FY2026 Q3, 20270 = FY2027.

Run `python valuation_engine.py research/<TICKER>/inputs.json` for a summary; `--json` dumps everything.
"""
from __future__ import annotations

import calendar
import copy
import datetime as dt
import json
import statistics
import sys

SCENARIOS = ("bear", "base", "bull")
CAPEX_LINE_ALIASES = {"资本开支", "Capex", "capex", "Capital expenditure"}
REVENUE_LINE_ALIASES = {"总收入", "Revenue", "revenue", "Total revenue"}
MARGIN_LINE_ALIASES = {"营业利润率", "Operating margin", "operating_margin"}
DEFAULT_DEBT_SPREAD = 0.015      # pretax cost of debt = risk-free + this when wacc.pretax_cost_of_debt is null (wacc.debt_spread overrides)
DEFAULT_PE_MIN_NET_MARGIN = 0.01 # the P/E leg is off for a scenario whose quarters 5-8 net income is at or below this share of revenue


def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


class Model:
    def __init__(self, inputs: dict):
        self.i = copy.deepcopy(inputs)   # the engine may anchor steady-state ROIC; never mutate the caller's dict
        self.L = inputs["lines"]
        self.periods = inputs["periods"]
        a = inputs["as_of"]
        self.fy, self.q = a["latest_reported_fy"], a["latest_reported_q"]
        self.bs_date = _d(a["balance_sheet_date"])
        self.latest_key = self.fy * 10 + self.q
        self.fc_quarters = [self.fy * 10 + k for k in range(self.q + 1, 5)]      # unreported quarters of the current FY
        self.fy1, self.fy2 = (self.fy + 1) * 10, (self.fy + 2) * 10                # consensus annual periods
        # further annual periods carried in the consensus block (a street to FY+5, say) extend the explicit period
        self.extra_years = sorted(int(p["key"]) for p in self.periods if p["q"] == 0 and p["status"] != "actual" and int(p["key"]) > self.fy2)
        self.last_explicit = self.extra_years[-1] if self.extra_years else self.fy2
        self.n_conv = inputs["blend"].get("convergence_years", 12)
        self.years_ext = [((self.last_explicit // 10 + k) * 10, k) for k in range(1, self.n_conv + 1)]  # extrapolated FYs, step k

    # ------------------------------------------------------------------ helpers
    def v(self, line: str, key: int, default=0.0) -> float:
        x = self.L.get(line, {}).get(str(key))
        return default if x is None else float(x)

    def has(self, line: str, key: int) -> bool:
        return self.L.get(line, {}).get(str(key)) is not None

    def prior_year(self, key: int) -> int:
        return key - 10

    def pp(self, line: str, key: int, scn: str) -> float:
        """Adjustment in percentage points for a line and period (0 when none)."""
        tot = 0.0
        for r in self.i["adjustments"]:
            if r["line"] == line and int(r["period_key"]) == key:
                tot += float(r.get(scn) or 0.0)
        return tot

    def segment_line(self, name: str) -> str:
        return f"seg:{name}"

    # ----------------------------------------------------- revenue adjustments
    def delta_revenue_lines(self, scn: str) -> dict[str, dict[int, float]]:
        """Δ revenue per business line (own adjustment only) for the forecast quarters, FY+1, FY+2.

        Quarter q: Δ = consensus of the same quarter a year earlier x pp.
        FY+1:      Δ = Δ(FY) x cons(FY+1)/cons(FY) + (cons(FY) + Δ(FY)) x pp, Δ(FY) = Σ quarterly Δ.
        FY+2:      same recursion from FY+1.
        """
        out = {}
        for seg in self.i["segments"]:
            line = self.segment_line(seg)
            d = {}
            for qk in self.fc_quarters:
                d[qk] = self.v(line, self.prior_year(qk)) * self.pp(seg, qk, scn)
            d_fy = sum(d.values())
            fy0 = self.fy * 10
            prev_k, prev_d = fy0, d_fy
            for yk in [self.fy1, self.fy2] + self.extra_years:
                cp, cc = self.v(line, prev_k), self.v(line, yk)
                d[yk] = (prev_d * cc / cp if cp else 0.0) + (cp + prev_d) * self.pp(seg, yk, scn)
                prev_k, prev_d = yk, d[yk]
            out[seg] = d
        # a "total revenue" adjustment line, if used, behaves like one more business line
        tot = {}
        for qk in self.fc_quarters:
            tot[qk] = self.v("revenue", self.prior_year(qk)) * sum(self.pp(a, qk, scn) for a in REVENUE_LINE_ALIASES)
        d_fy = sum(tot.values())
        prev_k, prev_d = self.fy * 10, d_fy
        for yk in [self.fy1, self.fy2] + self.extra_years:
            cp, cc = self.v("revenue", prev_k), self.v("revenue", yk)
            tot[yk] = (prev_d * cc / cp if cp else 0.0) + (cp + prev_d) * sum(self.pp(a, yk, scn) for a in REVENUE_LINE_ALIASES)
            prev_k, prev_d = yk, tot[yk]
        out["__total__"] = tot
        return out

    def segment_margin(self, seg: str, key: int) -> float:
        """Consensus operating margin of the segment a line belongs to (floored at 0; total margin if none)."""
        top = seg
        while self.i["segments"][top].get("parent"):
            top = self.i["segments"][top]["parent"]
        oi_line = self.i["segments"][top].get("oi_line")
        rev = self.v(self.segment_line(top), key)
        total_m = self.v("operating_income", key) / self.v("revenue", key) if self.v("revenue", key) else 0.0
        if oi_line and self.has(oi_line, key) and rev:
            return max(0.0, self.v(oi_line, key) / rev)
        return max(0.0, total_m)

    # ----------------------------------------------------------- scenario P&L
    def scenario_series(self, scn: str) -> dict:
        """Revenue … FCFF for the forecast quarters, FY+1 and FY+2 under one scenario."""
        S = self.i["scenarios"][scn]
        dl = self.delta_revenue_lines(scn)
        keys = self.fc_quarters + [self.fy1, self.fy2] + self.extra_years
        s = {k: {} for k in ["revenue", "operating_income", "pretax_income", "tax_rate", "net_income", "adjusted_net_income",
                             "diluted_shares", "eps", "dividends_total", "dps", "d_and_a", "sbc", "wc_increase",
                             "capex", "finance_lease_additions", "nopat", "fcff", "ebitda", "delta_revenue", "delta_oi"]}
        margin_pp_line = next(iter(MARGIN_LINE_ALIASES))
        for k in keys:
            d_rev = sum(dl[seg][k] for seg in self.i["segments"]) + dl["__total__"][k]
            d_oi = sum(dl[seg][k] * self.segment_margin(seg, k) for seg in self.i["segments"])
            cons_rev, cons_oi = self.v("revenue", k), self.v("operating_income", k)
            d_oi += dl["__total__"][k] * (cons_oi / cons_rev if cons_rev else 0.0)
            d_oi += (cons_rev + d_rev) * sum(self.pp(a, k, scn) for a in MARGIN_LINE_ALIASES)
            rev, oi = cons_rev + d_rev, cons_oi + d_oi
            pretax = oi + self.v("other_income", k)
            rate = self.v("tax_rate_consensus", k, None) if self.has("tax_rate_consensus", k) else (
                self.v("income_tax", k) / self.v("pretax_income", k) if self.v("pretax_income", k) else S["steady_tax"])
            eff = rate if (pretax > 0 and 0 <= rate <= 0.5) else S["steady_tax"]
            ni = pretax * (1 - eff)
            sh = self.v("diluted_shares", k)
            div = self.v("dividends_total", k) * (ni / self.v("net_income", k) if self.v("net_income", k) else 1.0)
            s["revenue"][k], s["operating_income"][k], s["pretax_income"][k] = rev, oi, pretax
            s["delta_revenue"][k], s["delta_oi"][k] = d_rev, d_oi
            s["tax_rate"][k], s["net_income"][k] = rate, ni
            s["adjusted_net_income"][k] = ni + self.v("adjustments", k)
            s["diluted_shares"][k], s["eps"][k] = sh, (ni / sh if sh else 0.0)
            s["dividends_total"][k], s["dps"][k] = div, (div / sh if sh else 0.0)
            s["d_and_a"][k], s["sbc"][k], s["wc_increase"][k] = self.v("d_and_a", k), self.v("sbc", k), self.v("wc_increase", k)
            s["finance_lease_additions"][k] = self.v("finance_lease_additions", k)
            s["nopat"][k] = oi * (1 - eff)
            s["ebitda"][k] = oi + s["d_and_a"][k]
        # capex: quarters = consensus + same quarter last year x pp; FY+1/FY+2 roll the current-FY delta forward
        cap_pp = lambda k: sum(self.pp(a, k, scn) for a in CAPEX_LINE_ALIASES)
        for qk in self.fc_quarters:
            s["capex"][qk] = self.v("capex", qk) + self.v("capex", self.prior_year(qk)) * cap_pp(qk)
        actual_q = [self.fy * 10 + k for k in range(1, self.q + 1)]
        cons_q_sum = sum(self.v("capex", k) for k in actual_q + self.fc_quarters)
        adj_fy0 = sum(self.v("capex", k) for k in actual_q) + sum(s["capex"][k] for k in self.fc_quarters)
        c0 = self.v("capex", self.fy * 10)
        prev_k, prev_adj, prev_cons = self.fy * 10, adj_fy0 - cons_q_sum + c0, c0
        for yk in [self.fy1, self.fy2] + self.extra_years:
            cc = self.v("capex", yk)
            s["capex"][yk] = cc + (prev_adj - prev_cons) * (cc / prev_cons if prev_cons else 0.0) + prev_adj * cap_pp(yk)
            prev_k, prev_adj, prev_cons = yk, s["capex"][yk], cc
        for k in keys:
            s["fcff"][k] = s["nopat"][k] + s["d_and_a"][k] - s["capex"][k] - s["finance_lease_additions"][k] - s["wc_increase"][k]
        return s

    # ----------------------------------------------------------- extrapolation
    def extrapolate(self, scn: str, s: dict) -> dict:
        """FY+3 … FY+2+N: growth, margin, tax and the net-reinvestment ratio converge linearly to steady state."""
        S = self.i["scenarios"][scn]
        g, m_ss, t_ss, roic = S["terminal_growth"], S["steady_margin"], S["steady_tax"], S["steady_roic"]
        N = self.n_conv
        y2 = self.last_explicit
        y1 = self.extra_years[-2] if len(self.extra_years) >= 2 else (self.fy2 if self.extra_years else self.fy1)
        rev2, rev1 = s["revenue"][y2], s["revenue"][y1]
        g2 = rev2 / rev1 - 1
        m2 = s["operating_income"][y2] / rev2
        t2 = s["tax_rate"][y2] if (s["pretax_income"][y2] > 0 and 0 <= s["tax_rate"][y2] <= 0.5) else t_ss
        da_ratio = s["d_and_a"][y2] / rev2
        wc_ratio = s["wc_increase"][y2] / (rev2 - rev1) if rev2 != rev1 else 0.0
        cap2, lease2 = s["capex"][y2], s["finance_lease_additions"][y2]
        lease_share = lease2 / cap2 if cap2 else 0.0
        r2 = (cap2 + lease2 - s["d_and_a"][y2] + s["wc_increase"][y2]) / rev2   # starting net reinvestment / revenue
        r_ss = g / roic * m_ss * (1 - t_ss)                                     # steady-state reinvestment / revenue
        e = {k: {} for k in ["growth", "revenue", "margin", "operating_income", "tax_rate", "d_and_a", "wc_increase",
                             "reinvest_ratio", "capex", "finance_lease_additions", "nopat", "fcff", "ebitda"]}
        e["reinvest_ratio_start"], e["reinvest_ratio_steady"] = r2, r_ss
        prev_rev = rev2
        for yk, k in self.years_ext:   # empty when convergence_years is 0 (exit-P/E valuations)
            f = k / N
            gr = g2 + (g - g2) * f
            rev = prev_rev * (1 + gr)
            mg = m2 + (m_ss - m2) * f
            tx = t2 + (t_ss - t2) * f
            oi = rev * mg
            da = rev * da_ratio
            wc = (rev - prev_rev) * wc_ratio
            rr = r2 + (r_ss - r2) * f
            capex = (rr * rev + da - wc) / (1 + lease_share)
            lease = capex * lease_share
            nopat = oi * (1 - tx)
            e["growth"][yk], e["revenue"][yk], e["margin"][yk], e["operating_income"][yk] = gr, rev, mg, oi
            e["tax_rate"][yk], e["d_and_a"][yk], e["wc_increase"][yk], e["reinvest_ratio"][yk] = tx, da, wc, rr
            e["capex"][yk], e["finance_lease_additions"][yk], e["nopat"][yk] = capex, lease, nopat
            e["fcff"][yk] = nopat + da - capex - lease - wc
            e["ebitda"][yk] = oi + da
            prev_rev = rev
        last = self.years_ext[-1][0] if self.years_ext else y2
        e["terminal_nopat"] = (e["nopat"][last] if self.years_ext else s["nopat"][y2]) * (1 + g)   # NOPAT of the year after the horizon
        e["implied_return_on_new_investment"] = {}
        yrs = [y2] + [yk for yk, _ in self.years_ext]
        nop = {**{y2: s["nopat"][y2]}, **e["nopat"]}
        reinv = {y2: cap2 + lease2 - s["d_and_a"][y2] + s["wc_increase"][y2],
                 **{yk: e["capex"][yk] + e["finance_lease_additions"][yk] - e["d_and_a"][yk] + e["wc_increase"][yk] for yk, _ in self.years_ext}}
        for a, b in zip(yrs[:-1], yrs[1:]):
            e["implied_return_on_new_investment"][a] = (nop[b] - nop[a]) / reinv[a] if reinv[a] > 0 else None
        e["implied_return_on_new_investment"][last] = (e["terminal_nopat"] - nop[last]) / reinv[last] if reinv[last] > 0 else None
        # the checks' cyclical rule: what the transition's reinvestment earns once margins are back at the steady (mid-cycle)
        # level, i.e. revenue added x steady margin after tax per dollar reinvested; equals steady ROIC in a steady state
        tot = sum(reinv.values())
        rev_end = (e["revenue"][last] if self.years_ext else rev2) * (1 + g)
        e["implied_return_through_cycle"] = (rev_end - rev2) * m_ss * (1 - t_ss) / tot if tot > 0 else None
        return e

    # ------------------------------------------------------------------- WACC
    def wacc(self) -> dict:
        W, M = self.i["wacc"], self.i["market"]
        ke = W["risk_free"] + W["beta"] * W["erp"]
        sh = self.v("diluted_shares", self.latest_key)
        mcap = M.get("market_cap_musd_override") or M["price"] / M.get("adr_ratio", 1.0) * sh / M.get("fx", 1.0)
        debt = self.v("debt", self.latest_key)
        # TTM effective tax rate over the last four reported quarters, clipped to [0, 1]
        last4 = [k for k in sorted(int(p["key"]) for p in self.periods if p["q"] != 0 and p["status"] == "actual") if k <= self.latest_key][-4:]
        pre = sum(self.v("pretax_income", k) for k in last4)
        tax = sum(self.v("income_tax", k) for k in last4)
        t_ttm = 0.0 if pre <= 0 else min(1.0, max(0.0, tax / pre))
        kd_pre, kd_src = W.get("pretax_cost_of_debt"), "inputs"
        if kd_pre is None:
            # no stated rate (a fresh fill, a no-debt filer): the risk-free rate plus a stated spread, said out loud
            spread = W.get("debt_spread", DEFAULT_DEBT_SPREAD)
            kd_pre, kd_src = W["risk_free"] + spread, f"risk-free + {spread:.2%} spread (wacc.pretax_cost_of_debt is null)"
        kd = kd_pre * (1 - t_ttm)
        we = mcap / (mcap + debt)
        wacc = we * ke + (1 - we) * kd
        if W.get("mode") == "manual" and W.get("value") is not None:
            wacc = W["value"]            # e.g. the average of Bloomberg's and FactSet's WACC, as the 美投 AMZN video does
        return {"cost_of_equity": ke, "market_cap": mcap, "debt": debt, "weight_equity": we, "weight_debt": 1 - we,
                "ttm_tax_rate": t_ttm, "pretax_cost_of_debt": kd_pre, "cost_of_debt_source": kd_src,
                "after_tax_cost_of_debt": kd, "wacc": wacc, "computed_wacc": we * ke + (1 - we) * kd, "mode": W.get("mode", "capm")}

    # -------------------------------------------------------------------- DCF
    def dcf(self, scn: str, s: dict, e: dict, w: dict) -> dict:
        S = self.i["scenarios"][scn]
        g, roic = S["terminal_growth"], S["steady_roic"]
        wacc, ke = w["wacc"], w["cost_of_equity"]
        bs = self.bs_date
        fye_m = self.i["company"]["fiscal_year_end_month"]
        fy_end = lambda y: dt.date(y, fye_m, calendar.monthrange(y, fye_m)[1])
        rows = []
        # current FY: only the unreported quarters' FCFF, discounted to the midpoint between the balance-sheet date and FY end
        fc = sum(s["fcff"][k] for k in self.fc_quarters)
        mid = bs + (fy_end(self.fy) - bs) / 2
        t = (mid - bs).days / 365
        rows.append({"period": self.fy * 10, "stage": 1, "fcff": fc, "t": t, "df": 1 / (1 + wacc) ** t})
        for yk, series in [(self.fy1, s), (self.fy2, s)] + [(yk, s) for yk in self.extra_years] + [(yk, e) for yk, _ in self.years_ext]:
            mid = fy_end(yk // 10) - dt.timedelta(days=182.6)
            t = (mid - bs).days / 365 + ((mid - bs).seconds / 86400) / 365
            rows.append({"period": yk, "stage": 1 if yk <= self.last_explicit else 2, "fcff": series["fcff"][yk], "t": t, "df": 1 / (1 + wacc) ** t})
        for r in rows:
            r["pv"] = r["fcff"] * r["df"]
        pv_stage1 = sum(r["pv"] for r in rows if r["stage"] == 1)
        pv_stage2 = sum(r["pv"] for r in rows if r["stage"] == 2)
        B = self.i["blend"]
        tmode = B.get("terminal_mode", "gordon")
        if tmode == "exit_pe":
            # 美投 AMZN style: the last explicit year's net income x an exit P/E, discounted from that year end; no transition years
            last_end = fy_end(self.last_explicit // 10)
            t_tv = (last_end - bs).days / 365
            exit_pe = S.get("exit_pe", S.get("target_multiple"))
            tv = s["net_income"][self.last_explicit] * exit_pe
        else:
            last_end = fy_end(self.years_ext[-1][0] // 10) if self.years_ext else fy_end(self.last_explicit // 10)
            t_tv = (last_end - bs).days / 365 - 0.5
            tv = e["terminal_nopat"] * (1 - g / roic) / (wacc - g)
        pv_tv = tv / (1 + wacc) ** t_tv
        if B.get("valuation_date", "balance_sheet") == "fy_end":
            # 美投 AMZN style: present values stated at the current fiscal year end instead of the balance-sheet date
            shift = (1 + wacc) ** ((fy_end(self.fy) - bs).days / 365)
            pv_stage1, pv_stage2, pv_tv = pv_stage1 * shift, pv_stage2 * shift, pv_tv * shift
            for r in rows:
                r["df"] *= shift; r["pv"] *= shift
        ev = pv_stage1 + pv_stage2 + pv_tv
        net_debt = self.v("debt", self.latest_key) - self.v("cash_and_st_investments", self.latest_key)
        if B.get("equity_bridge", True):
            equity = ev - net_debt - self.v("minority_interest", self.latest_key) + self.v("investments", self.latest_key)
        else:
            equity = ev                     # the 美投 AMZN video divides the DCF total by the share count without a net-debt bridge
        sh = self.i["market"].get("shares_override") or self.v("diluted_shares", self.latest_key)
        fx = self.i["market"].get("fx", 1.0) * self.i["market"].get("adr_ratio", 1.0)
        per_share = equity / sh * fx
        core_per_share = per_share
        # sum-of-the-parts add-ons (美投's TSLA method): businesses valued at a future-year multiple, discounted to the valuation date and added per share
        addons = []
        val_date = fy_end(self.fy) if B.get("valuation_date", "balance_sheet") == "fy_end" else bs
        for ad in B.get("sotp_addons", []):
            tv_s = ad["terminal_value"]; tv_a = tv_s.get(scn, tv_s.get("base")) if isinstance(tv_s, dict) else tv_s
            t_a = (fy_end(int(ad["year"])) - val_date).days / 365
            pv_a = tv_a / (1 + ad["discount_rate"]) ** t_a
            addons.append({"name": ad["name"], "year": int(ad["year"]), "discount_rate": ad["discount_rate"], "terminal_value": tv_a, "t": t_a, "pv": pv_a, "per_share": pv_a / sh * fx, "basis": ad.get("basis", "")})
            per_share += pv_a / sh * fx
        ntm_dps = self.ntm_dps(s)
        target = per_share * (1 + ke) - ntm_dps * fx if B.get("dcf_roll_forward", True) else per_share
        return {"rows": rows, "pv_stage1": pv_stage1, "pv_stage2": pv_stage2, "terminal_value": tv, "pv_terminal": pv_tv, "terminal_mode": tmode,
                "exit_pe": S.get("exit_pe") if tmode == "exit_pe" else None, "terminal_net_income": s["net_income"][self.last_explicit] if tmode == "exit_pe" else None,
                "t_terminal": t_tv, "enterprise_value": ev, "net_debt": net_debt, "investments": self.v("investments", self.latest_key),
                "equity_value": equity, "value_per_share": per_share, "core_per_share": core_per_share, "addons": addons, "ntm_dps": ntm_dps, "target": target,
                "terminal_share_of_ev": pv_tv / ev if ev else None,
                "implied_exit_ev_ebitda": (tv / e["ebitda"][self.years_ext[-1][0]]) if (self.years_ext and e["ebitda"][self.years_ext[-1][0]]) else None}

    def ntm_dps(self, s: dict) -> float:
        """Dividends per share over the next four quarters, starting with the latest reported quarter.

        A quarter inside the current fiscal year uses the (scenario) quarterly DPS; one beyond it uses next year's annual DPS / 4.
        """
        total, key = 0.0, self.latest_key
        for _ in range(4):
            y, q = key // 10, key % 10
            if key == self.latest_key:
                total += self.v("dps", key)
            elif y == self.fy:
                total += s["dps"].get(key, self.v("dps", key))
            else:
                total += s["dps"].get(y * 10, self.v("dps", y * 10)) / 4
            key = key + 1 if q < 4 else (y + 1) * 10 + 1
        return total

    # -------------------------------------------------------- relative value
    def multiples(self, scn: str, s: dict) -> dict:
        S = self.i["scenarios"][scn]
        basis = self.i["blend"].get("earnings_basis", "GAAP")
        n_actual = self.q
        w = (4 - n_actual) / 4                                       # weight of FY+1 in the "quarters 5-8" window
        ni_line = "net_income" if basis == "GAAP" else "adjusted_net_income"
        ni = w * s[ni_line][self.fy1] + (1 - w) * s[ni_line][self.fy2]
        sh = w * s["diluted_shares"][self.fy1] + (1 - w) * s["diluted_shares"][self.fy2]
        fx = self.i["market"].get("fx", 1.0) * self.i["market"].get("adr_ratio", 1.0)
        mult = S["target_multiple"]
        ra = self.i["blend"].get("multiple_rate_aware") or {}
        if ra.get("enabled"):
            # a multiple set when the 10-year was rf_ref is re-based to today's required return: m x (rf_ref + ERP) / (rf + ERP)
            W = self.i["wacc"]
            mult = mult * (ra.get("rf_ref", 0.05) + W["erp"]) / (W["risk_free"] + W["erp"])
        target = ni * mult / sh * fx
        # a negative or near-zero earnings base makes the multiple meaningless: the leg is off and blend_target gives its weight to the DCF
        rev = w * s["revenue"][self.fy1] + (1 - w) * s["revenue"][self.fy2]
        net_margin = ni / rev if rev else None
        disabled = net_margin is None or net_margin <= self.i["blend"].get("pe_min_net_margin", DEFAULT_PE_MIN_NET_MARGIN)
        raw_target, target = target, (None if disabled else target)
        price = self.i["market"]["price"]
        eps1 = s[ni_line][self.fy1] / s["diluted_shares"][self.fy1] * fx
        eps2 = s[ni_line][self.fy2] / s["diluted_shares"][self.fy2] * fx
        return {"weight_fy1": w, "q5_q8_net_income": ni, "q5_q8_shares": sh, "q5_q8_eps": ni / sh * fx, "target_multiple": mult, "stated_multiple": S["target_multiple"],
                "target": target, "raw_target": raw_target, "disabled": disabled, "q5_q8_net_margin": net_margin, "basis": basis,
                "implied_pe_fy1": target / eps1 if (eps1 and target is not None) else None, "implied_pe_fy2": target / eps2 if (eps2 and target is not None) else None,
                "price_implied_multiple": price / fx * sh / ni if ni else None, "eps_fy1": eps1, "eps_fy2": eps2}

    # -------------------------------------------------------------- top level
    # ------------------------------------------------------- returns on capital
    def incremental_roic(self, years: int = 2, floor_wc: bool = False) -> dict:
        """Realised return on the capital added over the last `years`: ΔNOPAT(TTM) / Σ(capex + leases − D&A + working capital),
        reported quarters only; floor_wc counts a working-capital release as zero (the checks' deferred-revenue rule)."""
        qs = sorted(int(p["key"]) for p in self.periods if p["q"] != 0 and p["status"] == "actual" and int(p["key"]) <= self.latest_key)
        n = 4 * years
        if len(qs) < n + 4:
            return {"incremental_roic": None, "note": "fewer than %d reported quarters" % (n + 4)}
        def nopat(k):
            if self.has("nopat", k):
                return self.v("nopat", k)
            pre, tax = self.v("pretax_income", k), self.v("income_tax", k)
            rate = tax / pre if pre > 0 else self.i["scenarios"]["base"]["steady_tax"]
            rate = rate if 0 <= rate <= 0.5 else self.i["scenarios"]["base"]["steady_tax"]
            return self.v("operating_income", k) * (1 - rate)
        now, then = qs[-4:], qs[-4 - n:-n]
        d_nopat = sum(nopat(k) for k in now) - sum(nopat(k) for k in then)
        window = qs[-n:]
        wc = (lambda k: max(0.0, self.v("wc_increase", k))) if floor_wc else (lambda k: self.v("wc_increase", k))
        reinvest = sum(self.v("capex", k) + self.v("finance_lease_additions", k) - self.v("d_and_a", k) + wc(k) for k in window)
        return {"incremental_roic": d_nopat / reinvest if reinvest > 0 else None, "nopat_ttm": sum(nopat(k) for k in now),
                "nopat_ttm_prior": sum(nopat(k) for k in then), "net_reinvestment": reinvest, "years": years,
                "window": [window[0], window[-1]]}

    def anchor_roic(self, w: dict) -> dict | None:
        """blend.steady_roic_anchor: pull the base steady-state ROIC down to the realised incremental ROIC when that is lower
        (floored at WACC + floor_over_wacc), and shift bear and bull by the same amount. Off by default."""
        cfg = self.i["blend"].get("steady_roic_anchor") or {}
        if not cfg.get("enabled"):
            return None
        r = self.incremental_roic(cfg.get("years", 2))
        if r.get("incremental_roic") is None:
            return None
        base0 = self.i["scenarios"]["base"]["steady_roic"]
        floor = w["wacc"] + cfg.get("floor_over_wacc", 0.02)
        anchored = min(base0, max(floor, r["incremental_roic"]))
        delta = anchored - base0
        for k in SCENARIOS:
            self.i["scenarios"][k]["steady_roic"] = max(floor, self.i["scenarios"][k]["steady_roic"] + delta)
        return {"template_base": base0, "anchored_base": anchored, "delta": delta, "floor": floor, "incremental_roic": r["incremental_roic"]}

    # ------------------------------------------------------------ reverse DCF
    def _solve(self, lo: float, hi: float, f, target: float, n: int = 40):
        flo, fhi = f(lo) - target, f(hi) - target
        if flo * fhi > 0:
            return None
        for _ in range(n):
            mid = (lo + hi) / 2
            fm = f(mid) - target
            if flo * fm <= 0:
                hi, fhi = mid, fm
            else:
                lo, flo = mid, fm
        return (lo + hi) / 2

    def implied(self, price: float) -> dict:
        """What the price assumes, base scenario: extra growth (pp on every forecast period), steady margin, steady ROIC."""
        base_inputs = copy.deepcopy(self.i)
        base_inputs["blend"]["steady_roic_anchor"] = {"enabled": False}
        periods = self.fc_quarters + [self.fy1, self.fy2]
        def blended_with_growth(x):
            inp = copy.deepcopy(base_inputs)
            inp["adjustments"] = [a for a in inp["adjustments"]] + [{"line": "Total revenue", "period_key": k, "bear": 0, "base": x, "bull": 0} for k in periods]
            m = Model(inp)
            s = m.scenario_series("base"); e = m.extrapolate("base", s); w = m.wacc()
            return m.blend_target(m.dcf("base", s, e, w)["target"], m.multiples("base", s)["target"])
        def dcf_with(key, x):
            inp = copy.deepcopy(base_inputs)
            inp["scenarios"]["base"][key] = x
            m = Model(inp)
            s = m.scenario_series("base"); e = m.extrapolate("base", s); w = m.wacc()
            return m.dcf("base", s, e, w)["target"]
        w = self.wacc()
        return {"growth_pp": self._solve(-0.30, 0.30, blended_with_growth, price),
                "steady_margin": self._solve(0.05, 0.70, lambda x: dcf_with("steady_margin", x), price),
                "steady_roic": self._solve(w["wacc"] + 0.005, 1.5, lambda x: dcf_with("steady_roic", x), price),
                "note": "growth_pp: percentage points added to consensus growth in every forecast period (house adjustments kept) so the base blended target equals the price; margin and ROIC: the base steady-state value at which the base DCF equals the price"}

    def blend_target(self, dcf_target: float, pe_target: float | None) -> float:
        """dcf_weight x DCF + the rest x P/E; a disabled P/E leg (None) hands its weight to the DCF."""
        if pe_target is None:
            return dcf_target
        dw = self.i["blend"]["dcf_weight"]
        return dw * dcf_target + (1 - dw) * pe_target

    def run(self) -> dict:
        w = self.wacc()
        anchor = self.anchor_roic(w)
        out = {"inputs_as_of": self.i["as_of"], "price": self.i["market"]["price"], "wacc": w, "scenarios": {},
               "returns": {**self.incremental_roic(), "steady_roic_base": self.i["scenarios"]["base"]["steady_roic"], "anchor": anchor},
               "warnings": []}
        if w["cost_of_debt_source"] != "inputs":
            out["warnings"].append(f"No pretax cost of debt in inputs.json: the WACC uses {w['pretax_cost_of_debt']:.2%} = {w['cost_of_debt_source']}")
        for scn in SCENARIOS:
            s = self.scenario_series(scn)
            e = self.extrapolate(scn, s)
            d = self.dcf(scn, s, e, w)
            m = self.multiples(scn, s)
            dw = self.i["blend"]["dcf_weight"]
            blended = self.blend_target(d["target"], m["target"])
            if m["disabled"]:
                out["warnings"].append(
                    f"{scn}: P/E leg disabled: quarters 5-8 {m['basis']} net income {m['q5_q8_net_income']:,.0f} is "
                    + (f"{m['q5_q8_net_margin']:.1%} of revenue" if m["q5_q8_net_margin"] is not None else "on no revenue")
                    + f" (floor {self.i['blend'].get('pe_min_net_margin', DEFAULT_PE_MIN_NET_MARGIN):.0%}); its {1 - dw:.0%} weight moved to the DCF")
            rev25 = self.v("revenue", (self.fy - 1) * 10)
            k30 = (self.fy + 4) * 10
            rev30 = s["revenue"][k30] if k30 in s["revenue"] else e["revenue"].get(k30)
            out["scenarios"][scn] = {"series": s, "extrapolation": e, "dcf": d, "multiples": m, "blended_target": blended,
                                     "upside": blended / self.i["market"]["price"] - 1,
                                     "revenue_cagr_5y": (rev30 / rev25) ** (1 / 5) - 1 if (rev25 and rev30) else None,
                                     "q5_q8_operating_margin": (m["weight_fy1"] * s["operating_income"][self.fy1] + (1 - m["weight_fy1"]) * s["operating_income"][self.fy2])
                                                               / (m["weight_fy1"] * s["revenue"][self.fy1] + (1 - m["weight_fy1"]) * s["revenue"][self.fy2])}
        p = self.i["blend"]["target_position"]
        b, ba, bu = (out["scenarios"][k] for k in SCENARIOS)

        def lerp(lo, mid, hi):   # None (a disabled P/E leg) where the position needs it
            if p == 0 or mid is None:
                return mid
            far = hi if p > 0 else lo
            return None if far is None else (mid + p * (far - mid) if p > 0 else mid + p * (mid - far))
        house = {"position": p,
                 "dcf_target": lerp(b["dcf"]["target"], ba["dcf"]["target"], bu["dcf"]["target"]),
                 "multiples_target": lerp(b["multiples"]["target"], ba["multiples"]["target"], bu["multiples"]["target"]),
                 "target": lerp(b["blended_target"], ba["blended_target"], bu["blended_target"])}
        house["upside"] = house["target"] / self.i["market"]["price"] - 1
        ni_h = lerp(b["multiples"]["q5_q8_net_income"], ba["multiples"]["q5_q8_net_income"], bu["multiples"]["q5_q8_net_income"])
        house["implied_multiple"] = house["multiples_target"] * ba["multiples"]["q5_q8_shares"] / ni_h if (ni_h and house["multiples_target"] is not None) else None
        out["house"] = house
        # probability-weighted value and a position size from reward to risk
        S = self.i["scenarios"]
        probs = {k: S[k].get("probability", {"bear": 0.25, "base": 0.5, "bull": 0.25}[k]) for k in SCENARIOS}
        tot = sum(probs.values()) or 1.0
        probs = {k: v / tot for k, v in probs.items()}
        price = self.i["market"]["price"]
        ev = sum(probs[k] * out["scenarios"][k]["blended_target"] for k in SCENARIOS)
        bear_t = out["scenarios"]["bear"]["blended_target"]
        downside = bear_t / price - 1                       # negative when the bear value is below the price
        rr = (ev - price) / (price - bear_t) if price > bear_t else float("inf")
        sz = self.i["blend"].get("sizing") or {}
        full_at = sz.get("full_at_reward_to_risk", 2.0)
        neutral = sz.get("neutral", 0.5)
        # linear in reward to risk: `neutral` at fair value, full at rr >= full_at, zero at rr <= -full_at (bear value far below price)
        exposure = 1.0 if rr == float("inf") else max(0.0, min(1.0, neutral + (1 - neutral) * rr / full_at))
        out["expected"] = {"probabilities": probs, "expected_target": ev, "expected_upside": ev / price - 1, "downside_to_bear": downside,
                           "reward_to_risk": rr, "exposure": exposure, "full_at_reward_to_risk": full_at, "neutral": neutral}
        try:
            out["implied"] = self.implied(price)
        except Exception as exc:  # noqa: BLE001
            out["implied"] = {"error": str(exc)}
        out["checks"] = self.checks(out)
        return out

    # ------------------------------------------------------------ full table
    def period_meta(self) -> list[dict]:
        """Every column of the model in order: actual periods, forecast quarters, FY, FY+1, FY+2, extrapolated years."""
        cols = []
        for p in self.periods:
            k = int(p["key"])
            status = "actual" if (p["status"] == "actual" and k <= self.latest_key or (p["q"] == 0 and k < self.fy * 10)) else "forecast"
            if k == self.fy * 10:
                status = "forecast"
            y, q = k // 10, k % 10
            label = f"FY{y}" if q == 0 else f"FY{y % 100} Q{q}"
            if status != "actual":
                label += "E"
            cols.append({"key": k, "label": label, "status": status, "annual": q == 0})
        for yk, _ in self.years_ext:
            cols.append({"key": yk, "label": f"FY{yk // 10}E", "status": "extrapolated", "annual": True})
        return cols

    def table(self, scn: str, s: dict | None = None, e: dict | None = None) -> dict:
        """{row id: {period key: value}} for one scenario, every column of period_meta()."""
        s = s or self.scenario_series(scn)
        e = e or self.extrapolate(scn, s)
        dl = self.delta_revenue_lines(scn)
        T: dict[str, dict[int, float]] = {}

        def put(row, k, v):
            if v is not None:
                T.setdefault(row, {})[k] = v

        fc = set(self.fc_quarters + [self.fy1, self.fy2] + self.extra_years)
        actual_q_fy = [self.fy * 10 + k for k in range(1, self.q + 1)]
        for col in self.period_meta():
            k = col["key"]
            if col["status"] == "extrapolated":
                for row in ("revenue", "operating_income", "tax_rate", "d_and_a", "wc_increase", "capex",
                            "finance_lease_additions", "nopat", "fcff", "ebitda", "reinvest_ratio"):
                    put(row, k, e[row][k])
                put("growth", k, e["growth"][k])
                put("margin", k, e["margin"][k])
                continue
            if k in fc:
                for row in ("revenue", "operating_income", "pretax_income", "tax_rate", "net_income", "adjusted_net_income",
                            "diluted_shares", "eps", "dividends_total", "dps", "d_and_a", "sbc", "wc_increase", "capex",
                            "finance_lease_additions", "nopat", "fcff", "ebitda"):
                    put(row, k, s[row][k])
                put("income_tax", k, s["pretax_income"][k] - s["net_income"][k])
                for seg in self.i["segments"]:
                    line = self.segment_line(seg)
                    if self.has(line, k):
                        d = dl[seg][k] + sum(dl[c][k] for c, m in self.i["segments"].items() if m.get("parent") == seg)
                        put(f"seg:{seg}", k, self.v(line, k) + d)
                        oi_line = self.i["segments"][seg].get("oi_line")
                        if oi_line and self.has(oi_line, k):
                            put(f"segoi:{seg}", k, self.v(oi_line, k) + d * self.segment_margin(seg, k))
                for row in ("adjustments", "buybacks", "operating_cash_flow", "cash_and_st_investments", "debt",
                            "investments", "minority_interest", "equity", "other_income"):
                    if self.has(row, k):
                        put(row, k, self.v(row, k))
            elif k == self.fy * 10:
                # current fiscal year: flows are the sum of the four quarters (actual + adjusted forecast)
                qs = actual_q_fy + self.fc_quarters
                get = lambda row, q: (s[row][q] if q in s.get(row, {}) and q in fc else self.v(row, q))
                for row in ("revenue", "operating_income", "pretax_income", "net_income", "dividends_total", "d_and_a",
                            "sbc", "wc_increase", "capex", "finance_lease_additions", "nopat", "fcff", "adjustments", "buybacks"):
                    put(row, k, sum(get(row, q) for q in qs))
                tax = sum((s["pretax_income"][q] - s["net_income"][q]) if q in fc else self.v("income_tax", q) for q in qs)
                put("income_tax", k, tax)
                rate = tax / T["pretax_income"][k] if T["pretax_income"][k] else None
                put("tax_rate", k, rate)
                # the workbook's annual NOPAT and FCFF are built from the annual sums, not the quarters
                S = self.i["scenarios"][scn]
                eff = rate if (rate is not None and T["pretax_income"][k] > 0 and 0 <= rate <= 0.5) else S["steady_tax"]
                T["nopat"][k] = T["operating_income"][k] * (1 - eff)
                T["fcff"][k] = T["nopat"][k] + T["d_and_a"][k] - T["capex"][k] - T["finance_lease_additions"][k] - T["wc_increase"][k]
                put("adjusted_net_income", k, T["net_income"][k] + T["adjustments"][k])
                sh = self.v("diluted_shares", k)
                put("diluted_shares", k, sh)
                put("eps", k, T["net_income"][k] / sh if sh else None)
                put("dps", k, self.v("dps", k))
                put("ebitda", k, T["operating_income"][k] + T["d_and_a"][k])
                for seg in self.i["segments"]:
                    line = self.segment_line(seg)
                    if all(self.has(line, q) for q in qs):
                        put(f"seg:{seg}", k, sum((T.get(f"seg:{seg}", {}).get(q, self.v(line, q))) for q in qs))
                    oi_line = self.i["segments"][seg].get("oi_line")
                    if oi_line and all(self.has(oi_line, q) for q in qs):
                        put(f"segoi:{seg}", k, sum((T.get(f"segoi:{seg}", {}).get(q, self.v(oi_line, q))) for q in qs))
                for row in ("operating_cash_flow", "cash_and_st_investments", "debt", "investments", "minority_interest",
                            "equity", "other_income"):
                    if self.has(row, k):
                        put(row, k, self.v(row, k))
            else:  # actual
                for row in ("revenue", "operating_income", "pretax_income", "income_tax", "net_income", "adjustments",
                            "adjusted_net_income", "diluted_shares", "dps", "dividends_total", "buybacks", "d_and_a", "sbc",
                            "wc_increase", "operating_cash_flow", "capex", "finance_lease_additions", "nopat", "fcff",
                            "cash_and_st_investments", "debt", "investments", "minority_interest", "equity", "ebitda",
                            "other_income"):
                    if self.has(row, k):
                        put(row, k, self.v(row, k))
                if self.has("revenue", k) and self.has("pretax_income", k) and self.v("pretax_income", k):
                    put("tax_rate", k, self.v("income_tax", k) / self.v("pretax_income", k))
                sh = self.v("diluted_shares", k)
                if sh and self.has("net_income", k):
                    put("eps", k, self.v("net_income", k) / sh)
                if self.has("adjusted_net_income", k) and sh:
                    put("adjusted_eps", k, self.v("adjusted_net_income", k) / sh)
                for seg in self.i["segments"]:
                    if self.has(f"seg:{seg}", k):
                        put(f"seg:{seg}", k, self.v(f"seg:{seg}", k))
                    oi_line = self.i["segments"][seg].get("oi_line")
                    if oi_line and self.has(oi_line, k):
                        put(f"segoi:{seg}", k, self.v(oi_line, k))
            # derived
            if T.get("revenue", {}).get(k):
                rev = T["revenue"][k]
                if T.get("operating_income", {}).get(k) is not None:
                    put("margin", k, T["operating_income"][k] / rev)
                if T.get("ebitda", {}).get(k) is None and T.get("d_and_a", {}).get(k) is not None and T.get("operating_income", {}).get(k) is not None:
                    put("ebitda", k, T["operating_income"][k] + T["d_and_a"][k])
                for seg in self.i["segments"]:
                    if T.get(f"segoi:{seg}", {}).get(k) is not None and T.get(f"seg:{seg}", {}).get(k):
                        put(f"segm:{seg}", k, T[f"segoi:{seg}"][k] / T[f"seg:{seg}"][k])
                if T.get("adjusted_net_income", {}).get(k) is not None and T.get("diluted_shares", {}).get(k):
                    put("adjusted_eps", k, T["adjusted_net_income"][k] / T["diluted_shares"][k])
                nd = (T.get("debt", {}).get(k) or 0) - (T.get("cash_and_st_investments", {}).get(k) or 0)
                if T.get("debt", {}).get(k) is not None and T.get("cash_and_st_investments", {}).get(k) is not None:
                    put("net_debt", k, nd)
                    eq = T.get("equity", {}).get(k)
                    nop = T.get("nopat", {}).get(k)
                    if eq and nop is not None and (eq + nd):
                        put("roic", k, nop * (1 if k % 10 == 0 else 4) / (eq + nd))
        # year-over-year growth for every flow row with a comparable period
        for row in ("revenue", "operating_income", "pretax_income", "net_income", "adjusted_net_income", "eps", "adjusted_eps",
                    "dps", "dividends_total", "d_and_a", "sbc", "operating_cash_flow", "capex", "ebitda", "diluted_shares",
                    *(self.segment_line(seg) for seg in self.i["segments"])):
            for k, v in list(T.get(row, {}).items()):
                p = T.get(row, {}).get(k - 10)
                if p:
                    put(f"yoy:{row}", k, v / p - 1)
        return T

    # ------------------------------------------------------------- company type
    def reported_years(self) -> list[int]:
        """Fiscal-year keys of the reported years in the lines (history before the periods included)."""
        last = self.fy if self.q == 4 else self.fy - 1
        return sorted(k for k in map(int, self.L.get("revenue", {})) if k % 10 == 0 and k // 10 <= last and self.v("revenue", k))

    def business_model(self) -> dict:
        """What the ROIC and reinvestment checks need to know about the company: company.business_model when declared
        ("standard", "cyclical", "deferred_revenue" or a list of them), otherwise detected from the reported fiscal years:
        cyclical when revenue fell 15% or more in a year, deferred revenue when the median working-capital build is below
        -1% of revenue (customers fund the growth: deferred revenue, prepayments, supplier float)."""
        decl = self.i["company"].get("business_model")
        if decl:
            types = {decl} if isinstance(decl, str) else set(decl)
            return {"types": types - {"standard"}, "why": {t: "declared" for t in types}}
        ys = self.reported_years()
        types, why = set(), {}
        falls = [(k, self.v("revenue", k) / self.v("revenue", k - 10) - 1) for k in ys if self.v("revenue", k - 10)]
        worst = min(falls, key=lambda x: x[1]) if falls else None
        if worst and worst[1] <= -0.15:
            types.add("cyclical")
            why["cyclical"] = f"detected: FY{worst[0] // 10} revenue {worst[1]:+.0%} y/y"
        wc = [self.v("wc_increase", k) / self.v("revenue", k) for k in ys if self.has("wc_increase", k)]
        if wc:
            med = statistics.median(wc)
            if med < -0.01:
                types.add("deferred_revenue")
                why["deferred_revenue"] = f"detected: median working-capital build {med:+.1%} of revenue, FY{ys[0] // 10}-FY{ys[-1] // 10}"
        return {"types": types, "why": why}

    def through_cycle_roic(self) -> dict | None:
        """Average annual ROIC (NOPAT / (equity + net debt) at the year end) over the reported fiscal years."""
        vals = []
        for k in self.reported_years():
            if not all(self.has(x, k) for x in ("operating_income", "equity", "debt", "cash_and_st_investments")):
                continue
            pre, tax = self.v("pretax_income", k), self.v("income_tax", k)
            rate = tax / pre if pre > 0 else self.i["scenarios"]["base"]["steady_tax"]
            rate = rate if 0 <= rate <= 0.5 else self.i["scenarios"]["base"]["steady_tax"]
            ic = self.v("equity", k) + self.v("debt", k) - self.v("cash_and_st_investments", k)
            if ic > 0:
                vals.append((k, self.v("operating_income", k) * (1 - rate) / ic))
        if not vals:
            return None
        return {"roic": sum(v for _, v in vals) / len(vals), "from": vals[0][0] // 10, "to": vals[-1][0] // 10, "n": len(vals)}

    def checks(self, out: dict) -> list[dict]:
        w = out["wacc"]["wacc"]
        S = self.i["scenarios"]
        R = self.i.get("reference_multiples", {})
        bm = self.business_model()
        cyc, dfr = "cyclical" in bm["types"], "deferred_revenue" in bm["types"]
        rule_cyc = f"cyclical rule ({bm['why'].get('cyclical')})"
        rule_dfr = f"deferred-revenue rule ({bm['why'].get('deferred_revenue')})"
        c = []
        g_max = max(S[k]["terminal_growth"] for k in SCENARIOS)   # S may carry a _note key
        c.append({"check": "WACC above terminal growth", "value": w - g_max, "ok": w - g_max > 0})
        r = out.get("returns", {})
        tc = self.through_cycle_roic() if cyc else None
        if tc:
            c.append({"check": f"Realised through-cycle average ROIC (FY{tc['from']}-FY{tc['to']}) at or above the base steady-state ROIC: {rule_cyc}",
                      "value": [tc["roic"], r["steady_roic_base"]], "ok": tc["roic"] >= r["steady_roic_base"], "warn_only": True, "rule": "cyclical"})
        else:
            ri = self.incremental_roic(floor_wc=True) if dfr else r
            if ri.get("incremental_roic") is not None:
                lab = f"{rule_dfr}: a working-capital release counts as zero reinvestment" if dfr else "standard rule"
                c.append({"check": f"Realised 2-year incremental ROIC at or above the base steady-state ROIC: {lab}", "value": [ri["incremental_roic"], r["steady_roic_base"]],
                          "ok": ri["incremental_roic"] >= r["steady_roic_base"], "warn_only": True, "rule": "deferred_revenue" if dfr else "standard"})
        roics = {k: S[k]["steady_roic"] for k in SCENARIOS}
        if cyc:
            probs = out["expected"]["probabilities"]
            avg = sum(probs[k] * roics[k] for k in SCENARIOS)
            c.append({"check": f"Steady-state ROIC at or above WACC, probability-weighted across scenarios (through-cycle; bear {roics['bear']:.1%}): {rule_cyc}",
                      "value": avg - w, "ok": avg >= w, "rule": "cyclical"})
        else:
            c.append({"check": "Steady-state ROIC at or above WACC (all scenarios): standard rule", "value": min(roics.values()) - w,
                      "ok": min(roics.values()) >= w, "rule": "standard"})
        t = [out["scenarios"][k]["blended_target"] for k in SCENARIOS]
        c.append({"check": "Scenario order bear <= base <= bull", "value": t, "ok": t[0] <= t[1] + 0.01 <= t[2] + 0.02})
        tv = out["scenarios"]["base"]["dcf"]["terminal_share_of_ev"]
        c.append({"check": "Terminal value share of EV (base) <= 80%", "value": tv, "ok": tv is not None and tv <= 0.8, "warn_only": True})
        if R.get("pe5y_low") is not None:
            m = S["base"]["target_multiple"]
            c.append({"check": "Base target multiple inside own 5-year forward range", "value": m,
                      "ok": R["pe5y_low"] <= m <= R["pe5y_high"], "warn_only": True})
        eb = out["scenarios"]["base"]["extrapolation"]
        irr = [v for v in eb["implied_return_on_new_investment"].values() if v is not None] if self.years_ext else []
        if cyc and self.years_ext and eb.get("implied_return_through_cycle") is not None:
            # a cyclical fading from a peak margin loses NOPAT while it reinvests: judge the reinvestment at the mid-cycle margin
            v = eb["implied_return_through_cycle"]
            c.append({"check": f"Implied return on new investment >= WACC through the transition (base, through-cycle: revenue added x steady margin after tax / cumulative reinvestment): {rule_cyc}",
                      "value": v, "ok": v >= w, "warn_only": True, "rule": "cyclical"})
        elif irr:
            c.append({"check": "Implied return on new investment >= WACC in every transition year (base): standard rule",
                      "value": min(irr), "ok": min(irr) >= w, "warn_only": True, "rule": "standard"})
        for scn in SCENARIOS:
            e = out["scenarios"][scn]["extrapolation"]
            r0, r_ss = e["reinvest_ratio_start"], e["reinvest_ratio_steady"]   # FY+2 consensus vs steady state
            if dfr:
                s = out["scenarios"][scn]["series"]
                wc_share = s["wc_increase"][self.last_explicit] / s["revenue"][self.last_explicit] if s["revenue"][self.last_explicit] else 0.0
                r0x = r0 - min(0.0, wc_share)      # a working-capital release is the business model, not disinvestment
                c.append({"check": f"Starting reinvestment rate > 0 and >= steady state ({scn}): {rule_dfr}: working capital {wc_share:+.1%} of revenue not counted against it",
                          "value": [r0x, r_ss], "ok": r0x > 0 and r0x >= r_ss, "warn_only": True, "rule": "deferred_revenue"})
            else:
                c.append({"check": f"Starting reinvestment rate > 0 and >= steady state ({scn}): standard rule", "value": [r0, r_ss],
                          "ok": r0 > 0 and r0 >= r_ss, "warn_only": True, "rule": "standard"})
        return c


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def summary(out: dict) -> str:
    p = out["price"]
    lines = [f"Price ${p:,.2f}  |  WACC {out['wacc']['wacc']:.2%}  (Ke {out['wacc']['cost_of_equity']:.2%}, E {out['wacc']['weight_equity']:.1%})",
             f"{'scenario':<10}{'DCF':>10}{'P/E':>10}{'blend':>10}{'upside':>9}{'rev CAGR':>10}{'TV/EV':>8}{'mult@px':>9}"]
    f = lambda x, spec, wd: (format(x, spec) if x is not None else "off").rjust(wd)   # "off": a disabled P/E leg
    for k in SCENARIOS:
        s = out["scenarios"][k]
        lines.append(f"{k:<10}{s['dcf']['target']:>10,.0f}{f(s['multiples']['target'], ',.0f', 10)}{s['blended_target']:>10,.0f}"
                     f"{s['upside']:>9.1%}{f(s['revenue_cagr_5y'], '.1%', 10)}{s['dcf']['terminal_share_of_ev']:>8.0%}{f(s['multiples']['price_implied_multiple'], '.1f', 9)}")
    h = out["house"]
    lines.append(f"{'house':<10}{h['dcf_target']:>10,.0f}{f(h['multiples_target'], ',.0f', 10)}{h['target']:>10,.0f}{h['upside']:>9.1%}"
                 f"{'':>10}{'':>8}{f(h['implied_multiple'], '.1f', 9)}")
    for wn in out.get("warnings", []):
        lines.append(f"WARNING: {wn}")
    ex, im, r = out.get("expected", {}), out.get("implied", {}), out.get("returns", {})
    if ex:
        lines.append(f"expected   target {ex['expected_target']:,.0f} ({ex['expected_upside']:+.1%}), downside to bear {ex['downside_to_bear']:+.1%}, "
                     f"reward/risk {ex['reward_to_risk']:.2f} -> exposure {ex['exposure']:.0%}")
    if im and "growth_pp" in im:
        g = f"{im['growth_pp'] * 100:+.1f}pp" if im['growth_pp'] is not None else "n/a"
        mg = f"{im['steady_margin']:.1%}" if im['steady_margin'] is not None else "n/a"
        rc = f"{im['steady_roic']:.1%}" if im['steady_roic'] is not None else "n/a"
        lines.append(f"price implies: growth {g} vs consensus | steady margin {mg} | steady ROIC {rc}")
    if r.get("incremental_roic") is not None:
        lines.append(f"realised 2y incremental ROIC {r['incremental_roic']:.1%} vs steady {r['steady_roic_base']:.0%}" + (f" (anchored from {r['anchor']['template_base']:.0%})" if r.get('anchor') else ""))
    for c in out["checks"]:
        flag = "ok " if c["ok"] else ("!  " if c.get("warn_only") else "FAIL")
        val = c["value"]
        if isinstance(val, float):
            val = f"{val:.4f}"
        elif isinstance(val, list):
            val = ", ".join(f"{x:.3f}" if isinstance(x, float) else str(x) for x in val)
        lines.append(f"  [{flag}] {c['check']}: {val}")
    return "\n".join(lines)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    inputs = load(args[0] if args else "inputs.json")
    result = Model(inputs).run()
    if "--json" in sys.argv:
        json.dump(result, sys.stdout, indent=1, default=str)
    else:
        print(summary(result))
