#!/usr/bin/env python3
"""Black-Scholes pricer for the paper-trading platform.

Importable:  from pricing import bs_price, structure_value
CLI:         python3 pricing.py SPOT STRIKE VIX_PCT DAYS_TO_EXPIRY {call|put}
Prints model premium per unit (1 NIFTY point = Rs 1; multiply by lot size 75).
"""
import sys, math


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bs_price(spot, strike, iv, days, opt_type, r=0.065, q=0.012):
    """Premium in index points. iv in percent (e.g. 13.8), days = calendar days to expiry."""
    t = max(days, 0.25) / 365.0  # floor at 6h to avoid zero
    sigma = iv / 100.0
    d1 = (math.log(spot / strike) + (r - q + sigma**2 / 2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    if opt_type == "call":
        return spot * math.exp(-q * t) * norm_cdf(d1) - strike * math.exp(-r * t) * norm_cdf(d2)
    return strike * math.exp(-r * t) * norm_cdf(-d2) - spot * math.exp(-q * t) * norm_cdf(-d1)


def structure_value(spot, strike, iv, days, opt_type, short_strike=None):
    """Value of a naked long option or a debit spread (long strike, short short_strike)."""
    v = bs_price(spot, strike, iv, days, opt_type)
    if short_strike:
        v -= bs_price(spot, short_strike, iv, days, opt_type)
    return v


if __name__ == "__main__":
    spot, strike, vix, days = map(float, sys.argv[1:5])
    opt = sys.argv[5].lower()
    print(f"{bs_price(spot, strike, vix, days, opt):.2f}")
