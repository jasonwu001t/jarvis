# `inputs.json` schema

One file per ticker folder; the engine, report and monitor read nothing else. USD millions unless
per share; rates as fractions; period keys `year*10 + quarter` as strings inside `lines`.

```jsonc
{
  "company": {"ticker": "META", "name": "Meta Platforms", "currency": "USD", "fiscal_year_end_month": 12},
  "as_of": {
    "latest_reported_fy": 2026, "latest_reported_q": 2, "balance_sheet_date": "2026-06-30",
    "consensus_date": "2026-10-15", "consensus_source": "where the consensus block came from",
    "method_source": "free text"
  },
  "market": {"price": 735.0, "price_date": "2026-10-13", "fx": 1.0, "adr_ratio": 1.0,
             "market_cap_musd_override": null,             // null: price × diluted shares
             "shares_override": null},                     // optional: per-share divisor (美投 AMZN: 10783)
  "wacc": {"beta": 1.43, "risk_free": 0.05, "erp": 0.042, "pretax_cost_of_debt": 0.0413,
           "risk_free_mode": "dgs10",                      // dgs10 (live) | manual
           "beta_mode": "adjusted_2y_weekly",              // adjusted_2y_weekly (live) | manual
           "mode": "capm", "value": null},                 // "manual" + value: fixed WACC (美投 AMZN 0.138); CAPM still shown
  "scenarios": {                                            // bear / base / bull, all five keys each
    "bear": {"terminal_growth": 0.035, "steady_roic": 0.20, "steady_margin": 0.35, "steady_tax": 0.149, "target_multiple": 18,
             "exit_pe": 20},                                // only read when blend.terminal_mode is "exit_pe"
    "base": {...}, "bull": {...}
  },
  "blend": {"dcf_weight": 0.5, "target_position": 0.05,    // house target: fraction from base toward bull (negative: toward bear)
            "multiple_type": "P/E", "earnings_basis": "GAAP", "convergence_years": 12,   // 0 = no transition years
            "terminal_mode": "gordon",                      // gordon (template) | exit_pe (last explicit year NI x exit_pe)
            "valuation_date": "balance_sheet",              // balance_sheet (template) | fy_end (PVs restated at the current FY end)
            "equity_bridge": true, "dcf_roll_forward": true, // false / false: 美投 AMZN (DCF total / shares, no roll-forward)
            "sotp_addons": [],                              // 美投 TSLA: [{name, year, discount_rate, terminal_value: {bear, base, bull}, basis}]
            "sizing": {"full_at_reward_to_risk": 2.0, "neutral": 0.5},            // expected-value exposure (valuation-method.md)
            "multiple_rate_aware": {"enabled": true, "rf_ref": 0.05},             // m x (rf_ref + ERP)/(rf + ERP)
            "steady_roic_anchor": {"enabled": true, "years": 2, "floor_over_wacc": 0.02},
            "overlays": {"enabled": true, "regime": {"nfci_max": 0.0, "vix_max": 30, "baa10y_max": 0.025, "cap": 0.5},
                         "vol": {"target": 0.35, "window": 60, "floor": 0.25}, "trend": {"sma": 200, "max_step_below": 0.25}}},
  // scenarios also carry "probability" (bear/base/bull, normalised); monitor carries "position_source" (expected_value | rules)
  // and "current_exposure" (fraction of full size, for trend staging); rules carry "exposure" (fraction, or null = keep / informational)
  "rating": {"label": "Positive"},
  "thesis": {"summary": "one paragraph, shown in the report's House view", "source": "..."},
  "adjustments": [                                          // pp added to consensus growth; line = a segment name,
    {"line": "Advertising", "period_key": 20263, "bear": 0, "base": 0.03, "bull": 0.05},   //   "Capex", "Total revenue" or "Operating margin"
    {"line": "Capex", "period_key": 20270, "bear": 0, "base": 0.05, "bull": 0.08}
  ],
  "reference_multiples": {"current_fwd_pe": 20.0, "pe5y_low": 14.6, "pe5y_avg": 18.7, "pe5y_high": 22.8},
  "segments": {                                             // name -> parent (null for top level) and the line holding its operating income
    "Family of Apps": {"parent": null, "oi_line": "segoi:Family of Apps"},
    "Advertising": {"parent": "Family of Apps"},
    "Reality Labs": {"parent": null, "oi_line": "segoi:Reality Labs"}
  },
  "periods": [{"key": 20240, "year": 2024, "q": 0, "status": "actual"}, ..., {"key": 20280, "year": 2028, "q": 0, "status": "consensus"}],
                                                            // consensus FYs beyond FY+2 (e.g. 20290..20310) extend the explicit period
  "lines": {                                                // {period key: value}; actual periods and the consensus block together
    "revenue": {}, "operating_income": {}, "pretax_income": {}, "income_tax": {}, "net_income": {},
    "adjustments": {}, "adjusted_net_income": {}, "diluted_shares": {}, "dps": {}, "dividends_total": {}, "buybacks": {},
    "d_and_a": {}, "sbc": {}, "wc_increase": {}, "operating_cash_flow": {}, "capex": {}, "finance_lease_additions": {},
    "nopat": {}, "fcff": {},                                 // actual periods only; the engine computes the forecast
    "cash_and_st_investments": {}, "debt": {}, "investments": {}, "minority_interest": {}, "equity": {}, "other_income": {},
    "seg:<Segment>": {}, "segoi:<Segment>": {}              // segment revenue and operating income
  },
  "baseline": {"label": "Template 2026-10-15 ($735)", "bear": 610.43, "base": 826.44, "bull": 901.10, "house": 830.17,
               "price": 735, "risk_free": 0.05, "beta": 1.43, "wacc": 0.1057},   // optional: shown beside live numbers so drift is visible
  "monitor": {"rules": [                                    // Python expressions over price, house_target, house_upside,
    {"name": "Below bear case", "when": "price <= bear_target", "action": "..."}   //   bear/base/bull_target, price_implied_pe_base, pe5y_low/high
  ]}
}
```

Conventions the engine relies on: the periods list carries every actual period and every consensus
period in time order; the current fiscal year's annual consensus (`<fy>0`) exists alongside its
quarters; FY+1 and FY+2 annual consensus exist; segment lines exist for the same periods as revenue
when segments are used. `scripts/new_ticker.py` writes a commented skeleton with all keys.
