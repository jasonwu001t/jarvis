"""Market-risk overlays applied on top of the valuation signal: regime gate, volatility scaling, trend filter.

All inputs are official or exchange series: Chicago Fed NFCI, Moody's Baa spread over the 10-year (BAA10Y),
VIX close (FRED), daily closes (Alpaca bars). Configuration lives in inputs.json -> blend.overlays:

  "overlays": {"enabled": true,
               "regime": {"nfci_max": 0.0, "vix_max": 30, "baa10y_max": 0.025, "cap": 0.5},
               "vol": {"target": 0.35, "window": 60, "floor": 0.25},
               "trend": {"sma": 200, "max_step_below": 0.25}}

regime: when any series is past its threshold the exposure is capped at `cap`.
vol:    exposure x min(1, target / realised vol) with a floor on the multiplier (annualised, log returns over `window` days).
trend:  below the SMA an increase in exposure is limited to `max_step_below` per decision (stage in); decreases are free.
"""
from __future__ import annotations

import datetime as dt
import math
import statistics

DEFAULT = {"enabled": True,
           "regime": {"nfci_max": 0.0, "vix_max": 30.0, "baa10y_max": 0.025, "cap": 0.5},
           "vol": {"target": 0.35, "window": 60, "floor": 0.25},
           "trend": {"sma": 200, "max_step_below": 0.25}}


def last_on_or_before(series: dict, d: str):
    keys = [k for k in series if k <= d]
    return (max(keys), series[max(keys)]) if keys else (None, None)


def market_state(prices: dict, d: str, macro: dict, cfg: dict | None = None) -> dict:
    """prices: {date: close}; macro: {"nfci": {date: v}, "vix": {date: v}, "baa10y": {date: v (fraction)}}."""
    cfg = {**DEFAULT, **(cfg or {})}
    rg, vc, tc = {**DEFAULT["regime"], **cfg.get("regime", {})}, {**DEFAULT["vol"], **cfg.get("vol", {})}, {**DEFAULT["trend"], **cfg.get("trend", {})}
    days = sorted(k for k in prices if k <= d)
    px = prices[days[-1]] if days else None
    sma = statistics.fmean(prices[k] for k in days[-tc["sma"]:]) if len(days) >= tc["sma"] else None
    rets = [math.log(prices[b] / prices[a]) for a, b in zip(days[-vc["window"] - 1:-1], days[-vc["window"]:])] if len(days) > vc["window"] else []
    vol = statistics.stdev(rets) * math.sqrt(252) if len(rets) > 5 else None
    nf_d, nf = last_on_or_before(macro.get("nfci", {}), d)
    vx_d, vx = last_on_or_before(macro.get("vix", {}), d)
    ba_d, ba = last_on_or_before(macro.get("baa10y", {}), d)
    stress = []
    if nf is not None and nf > rg["nfci_max"]:
        stress.append(f"NFCI {nf:+.2f} > {rg['nfci_max']:+.2f}")
    if vx is not None and vx > rg["vix_max"]:
        stress.append(f"VIX {vx:.0f} > {rg['vix_max']:.0f}")
    if ba is not None and ba > rg["baa10y_max"]:
        stress.append(f"Baa spread {ba:.2%} > {rg['baa10y_max']:.2%}")
    vol_scale = max(vc["floor"], min(1.0, vc["target"] / vol)) if vol else 1.0
    return {"date": d, "price": px, "sma": sma, "above_sma": (px >= sma) if (px and sma) else None,
            "realized_vol": vol, "vol_scale": vol_scale, "nfci": nf, "nfci_date": nf_d, "vix": vx, "vix_date": vx_d,
            "baa10y": ba, "baa10y_date": ba_d, "stress": stress, "regime_cap": rg["cap"] if stress else 1.0,
            "max_step_below": tc["max_step_below"], "enabled": cfg.get("enabled", True)}


def apply(signal_exposure: float, state: dict, current: float | None = None) -> dict:
    """Signal exposure (rules or expected value) -> recommended exposure after the overlays.

    current: the position now (fraction of full); None = unknown, trend staging is then reported but not applied."""
    if not state.get("enabled", True):
        return {"signal": signal_exposure, "after_regime": signal_exposure, "after_vol": signal_exposure, "recommended": signal_exposure, "staged": False}
    after_regime = min(signal_exposure, state["regime_cap"])
    after_vol = after_regime * state["vol_scale"]
    rec, staged = after_vol, False
    if current is not None and state.get("above_sma") is False and rec > current:
        rec, staged = min(rec, current + state["max_step_below"]), True
    return {"signal": signal_exposure, "after_regime": after_regime, "after_vol": after_vol, "recommended": rec, "staged": staged}
