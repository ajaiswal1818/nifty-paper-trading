#!/usr/bin/env python3
"""Backtest of strategy v1 (news-driven directional NIFTY weeklies), Jun 15 - Jul 14 2026.
Same rules as STRATEGY.md: score >= +2 buy ATM call, <= -2 buy ATM put, 1 lot (75),
stop -30%, target +50%, time-stop day before expiry (evening), reversal exit,
no entry with expiry today/tomorrow, no same-direction duplicate, max 2 positions,
max 35% capital as premium. BS pricing, IV = India VIX, r=6.5%, q=1.2%,
friction: buy at model*1.015, sell at model*0.985, Rs 100 flat per side.

Morning score uses only pre-open-knowable info: GIFT gap, overnight S&P 500,
last published FII daily net, overnight/weekend news. Where the actual open was
not reported, open is estimated as prev_close * (1 +/- 0.35% per GIFT direction).
"""
import math, json
from datetime import date

def norm_cdf(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def bs(spot, strike, vix, days, typ, r=0.065, q=0.012):
    t = max(days, 0.25) / 365.0
    s = vix / 100.0
    d1 = (math.log(spot / strike) + (r - q + s * s / 2) * t) / (s * math.sqrt(t))
    d2 = d1 - s * math.sqrt(t)
    if typ == "call":
        return spot * math.exp(-q * t) * norm_cdf(d1) - strike * math.exp(-r * t) * norm_cdf(d2)
    return strike * math.exp(-r * t) * norm_cdf(-d2) - spot * math.exp(-q * t) * norm_cdf(-d1)

LOT = 75
FEE = 100.0
EXPIRIES = [date(2026,6,16), date(2026,6,23), date(2026,6,30), date(2026,7,7), date(2026,7,14), date(2026,7,21)]

# date, open(actual/est), close, vix_close, vix_prev(morning IV), score, score_notes
DAYS = [
 (date(2026,6,15), 23705.1, 23853.90, 14.35, 14.72, +3, "GIFT up+1, US Fri +0.50+1, FII na 0, news US-Iran peace deal/crude -4% +1"),
 (date(2026,6,16), 23930.0, 23989.15, 13.36, 14.35, +2, "GIFT flat 0, US +1.8+1, FII na 0, ceasefire optimism +1"),
 (date(2026,6,17), 23989.2, 24085.70, 13.18, 13.36, -1, "GIFT flat 0, US -0.57-1, FII na 0, Fed caution mixed 0"),
 (date(2026,6,18), 24085.7, 24168.00, 12.67, 13.18, -2, "GIFT flat 0, US -1.21-1, FII na 0, Fed hawkish pause overnight -1"),
 (date(2026,6,19), 23958.85, 24013.10, 12.97, 12.67, -1, "GIFT down-1, US +1.0+1, FII na 0, Accenture guidance cut overnight -1"),
 (date(2026,6,22), 24123.0, 24102.90, 12.84, 12.97, +4, "GIFT up+1, US Thu +1.08+1, FII Fri +4859+1, US-Iran talks progress +1"),
 (date(2026,6,23), 24071.6, 23824.10, 13.94, 12.84, +1, "GIFT up+1, US -0.39 0, FII na 0, no strong pre-open news 0"),
 (date(2026,6,24), 23907.5, 24021.65, 13.38, 13.94, +1, "GIFT up+1, US -1.42-1, FII +18 0, Hormuz transit resumed overnight +1"),
 (date(2026,6,25), 24125.85, 24056.00, 13.05, 13.38, +2, "GIFT up+1, US -0.10 0, FII na 0, crude to pre-war/Micron +1"),
 (date(2026,6,29), 24056.0, 23946.25, 13.61, 13.05, -1, "GIFT flat 0, US Fri -0.05 0, FII na 0, weekend hostilities resumed -1"),
 (date(2026,6,30), 23946.3, 23865.75, 13.47, 13.61, -1, "GIFT flat 0, US +1.18+1, FII Mon -1350-1, ceasefire violation claims -1"),
 (date(2026,7,1),  23949.3, 24005.85, 13.24, 13.47, +1, "GIFT up+1, US +0.79+1, FII Tue -2557-1, mixed news 0"),
 (date(2026,7,2),  24089.9, 24175.70, 12.28, 13.24, +2, "GIFT up+1, US -0.22 0, FII na 0, Doha talks concluded/Warsh dovish +1"),
 (date(2026,7,3),  24260.3, 24270.85, 11.83, 12.28, +2, "GIFT up+1, US flat 0, FII na 0, soft US labour data overnight +1"),
 (date(2026,7,6),  24352.4, 24430.35, 11.81, 11.83, +2, "GIFT up+1, US Thu +0.01 0, FII na 0, HDFC Bank Q1/crude<72 +1"),
 (date(2026,7,7),  24430.4, 24398.70, 11.65, 11.81, +2, "GIFT na 0, US +0.72+1, FII Mon +2276+1, mixed 0"),
 (date(2026,7,8),  24239.0, 23882.05, 14.68, 11.65, -2, "GIFT down-1, US -0.45 0, FII +393 0, Kospi -5.65/US tech selloff/Iran -1"),
 (date(2026,7,9),  23930.0, 23962.80, 13.36, 14.68, +2, "GIFT flat 0, US -0.28 0, FII Wed +1365+1, relief/crude easing +1"),
 (date(2026,7,10), 24046.7, 24206.90, 12.55, 13.36, +3, "GIFT up+1, US +0.81+1, FII -533 0, global rebound +1"),
 (date(2026,7,13), 24039.4, 24211.00, 13.24, 12.55, -1, "GIFT down-1, US Fri +0.49 0, FII Fri +2604+1, weekend Iran escalation/Hormuz -1"),
 (date(2026,7,14), 24141.0, 24052.05, 13.80, 13.24, -4, "GIFT down-1, US -0.79-1, FII Mon -3062-1, blockade/Brent$84 -1"),
]

def pick_expiry(d):
    for e in EXPIRIES:
        if (e - d).days >= 2:
            return e
    return None

cash = 100000.0
positions = []  # dicts
log = []
curve = []

def mark(pos, spot, vix, d, extra_frac=0.0):
    days = (pos["expiry"] - d).days + extra_frac
    return bs(spot, pos["strike"], vix, days, pos["type"])

def close_pos(pos, spot, vix, d, when, reason, extra_frac=0.0):
    global cash
    model = mark(pos, spot, vix, d, extra_frac)
    proceeds = model * 0.985 * LOT - FEE
    cash += proceeds
    pnl = proceeds - pos["cost"]
    log.append((d.isoformat(), when, f"EXIT {pos['type'].upper()} {pos['strike']} exp {pos['expiry'].strftime('%d%b')}",
                f"{model:.1f}pts", f"{pnl:+,.0f}", reason))
    positions.remove(pos)

for d, o, c, vixc, vixp, score, notes in DAYS:
    # ---- MORNING (executed at open) ----
    for pos in positions[:]:
        m = mark(pos, o, vixp, d, 0.25)
        if (score >= 2 and pos["type"] == "put") or (score <= -2 and pos["type"] == "call"):
            close_pos(pos, o, vixp, d, "open", f"signal reversal (score {score:+d})", 0.25)
        elif m <= 0.70 * pos["entry_premium"]:
            close_pos(pos, o, vixp, d, "open", "stop loss -30%", 0.25)
        elif m >= 1.50 * pos["entry_premium"]:
            close_pos(pos, o, vixp, d, "open", "target +50%", 0.25)
    if abs(score) >= 2:
        typ = "call" if score > 0 else "put"
        if not any(p["type"] == typ for p in positions) and len(positions) < 2:
            exp = pick_expiry(d)
            if exp:
                strike = round(o / 50) * 50
                days = (exp - d).days + 0.25
                model = bs(o, strike, vixp, days, typ)
                cost = model * 1.015 * LOT + FEE
                deployed = sum(p["cost"] for p in positions) + cost
                equity_now = cash + sum(mark(p, o, vixp, d, 0.25) * LOT for p in positions)
                if cost <= 0.35 * equity_now:
                    cash -= cost
                    positions.append({"type": typ, "strike": strike, "expiry": exp,
                                      "entry_premium": model, "cost": cost, "entry_date": d})
                    log.append((d.isoformat(), "open", f"BUY {typ.upper()} {strike} exp {exp.strftime('%d%b')}",
                                f"{model:.1f}pts (Rs{cost:,.0f})", "", notes))
    # ---- EVENING (executed at close) ----
    for pos in positions[:]:
        m = mark(pos, c, vixc, d, 0.0)
        if m <= 0.70 * pos["entry_premium"]:
            close_pos(pos, c, vixc, d, "close", "stop loss -30%")
        elif m >= 1.50 * pos["entry_premium"]:
            close_pos(pos, c, vixc, d, "close", "target +50%")
        elif (pos["expiry"] - d).days <= 1:
            close_pos(pos, c, vixc, d, "close", "time stop (expires tomorrow)")
    unreal = sum(mark(p, c, vixc, d) * LOT - p["cost"] for p in positions)
    equity = cash + sum(mark(p, c, vixc, d) * LOT for p in positions)
    curve.append((d.isoformat(), c, vixc, score, round(cash), round(unreal), round(equity), len(positions)))

print("=== TRADE LOG ===")
for row in log:
    print(" | ".join(str(x) for x in row))
print("\n=== EQUITY CURVE (evening marks) ===")
print("date | close | vix | score | cash | unreal | equity | pos")
for row in curve:
    print(" | ".join(str(x) for x in row))
final = curve[-1][6]
print(f"\nFINAL EQUITY: Rs {final:,}  |  P&L: Rs {final-100000:+,} ({(final-100000)/1000:.1f}%)")
wins = [r for r in log if r[4] and float(r[4].replace(',','').replace('+','')) > 0]
losses = [r for r in log if r[4] and float(r[4].replace(',','').replace('+','')) < 0]
print(f"Closed trades: {len(wins)+len(losses)} | wins {len(wins)} | losses {len(losses)}")
