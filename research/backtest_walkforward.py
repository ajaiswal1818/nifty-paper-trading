#!/usr/bin/env python3
"""Walk-forward backtest.
Window A (train): May 15 - Jun 12 2026. Window B (test): Jun 15 - Jul 14 2026.
v1 = original rules. v2 = tuned ONLY on window A diagnostics.
Runs: v1(A), v2(A) in-sample, v1(B) [reference], v2(B) out-of-sample,
and FULL walk-forward: v1 live May 15-Jun 12, strategy upgraded to v2 over
the Jun 13-14 weekend, v2 live Jun 15-Jul 14, capital carried throughout.
"""
import math
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

LOT, FEE = 75, 100.0
EXPIRIES = [date(2026,5,19), date(2026,5,26), date(2026,6,2), date(2026,6,9),
            date(2026,6,16), date(2026,6,23), date(2026,6,30), date(2026,7,7),
            date(2026,7,14), date(2026,7,21)]

# (date, open, prev_close, close, vix_close, vix_prev, morning_score)
MAY = [
 (date(2026,5,15), 23731.4, 23689.6, 23643.50, 18.85, 19.00, +3),
 (date(2026,5,18), 23482.2, 23643.5, 23649.95, 19.63, 18.85, -2),
 (date(2026,5,19), 23675.3, 23649.95, 23618.00, 18.68, 19.63, +2),
 (date(2026,5,20), 23535.3, 23618.0, 23659.00, 18.70, 18.68, -3),
 (date(2026,5,21), 23830.05, 23659.0, 23654.70, 17.50, 18.70, +2),
 (date(2026,5,22), 23654.7, 23654.7, 23719.30, 17.00, 17.50, 0),
 (date(2026,5,25), 23940.3, 23719.3, 24031.70, 16.70, 17.00, +1),
 (date(2026,5,26), 24115.8, 24031.7, 23913.70, 16.13, 16.70, +2),
 (date(2026,5,27), 23880.35, 23913.7, 23907.15, 14.98, 16.13, 0),
 (date(2026,5,29), 23802.15, 23907.15, 23547.75, 16.19, 14.98, 0),
 (date(2026,6,1),  23630.2, 23547.75, 23382.60, 16.50, 16.19, -1),
 (date(2026,6,2),  23300.8, 23382.6, 23483.55, 16.40, 16.50, -2),
 (date(2026,6,3),  23401.4, 23483.55, 23405.60, 16.28, 16.40, -3),
 (date(2026,6,4),  23323.7, 23405.6, 23416.55, 15.88, 16.28, -3),
 (date(2026,6,5),  23478.55, 23416.55, 23366.70, 15.80, 15.88, 0),
 (date(2026,6,8),  23080.7, 23366.7, 23123.00, 17.09, 15.80, -3),
 (date(2026,6,9),  23123.0, 23123.0, 23242.00, 15.58, 17.09, +1),
 (date(2026,6,10), 23242.0, 23242.0, 23214.60, 15.60, 15.58, -1),
 (date(2026,6,11), 23133.3, 23214.6, 23161.60, 15.61, 15.60, -4),
 (date(2026,6,12), 23411.0, 23161.6, 23622.90, 14.72, 15.61, +3),
]
JUN = [
 (date(2026,6,15), 23705.1, 23622.9, 23853.90, 14.35, 14.72, +3),
 (date(2026,6,16), 23930.0, 23853.9, 23989.15, 13.36, 14.35, +2),
 (date(2026,6,17), 23989.2, 23989.15, 24085.70, 13.18, 13.36, -1),
 (date(2026,6,18), 24085.7, 24085.7, 24168.00, 12.67, 13.18, -2),
 (date(2026,6,19), 23958.85, 24168.0, 24013.10, 12.97, 12.67, -1),
 (date(2026,6,22), 24123.0, 24013.1, 24102.90, 12.84, 12.97, +4),
 (date(2026,6,23), 24071.6, 24102.9, 23824.10, 13.94, 12.84, +1),
 (date(2026,6,24), 23907.5, 23824.1, 24021.65, 13.38, 13.94, +1),
 (date(2026,6,25), 24125.85, 24021.65, 24056.00, 13.05, 13.38, +2),
 (date(2026,6,29), 24056.0, 24056.0, 23946.25, 13.61, 13.05, -1),
 (date(2026,6,30), 23946.3, 23946.25, 23865.75, 13.47, 13.61, -1),
 (date(2026,7,1),  23949.3, 23865.75, 24005.85, 13.24, 13.47, +1),
 (date(2026,7,2),  24089.9, 24005.85, 24175.70, 12.28, 13.24, +2),
 (date(2026,7,3),  24260.3, 24175.7, 24270.85, 11.83, 12.28, +2),
 (date(2026,7,6),  24352.4, 24270.85, 24430.35, 11.81, 11.83, +2),
 (date(2026,7,7),  24430.4, 24430.35, 24398.70, 11.65, 11.81, +2),
 (date(2026,7,8),  24239.0, 24398.7, 23882.05, 14.68, 11.65, -2),
 (date(2026,7,9),  23930.0, 23882.05, 23962.80, 13.36, 14.68, +2),
 (date(2026,7,10), 24046.7, 23962.8, 24206.90, 12.55, 13.36, +3),
 (date(2026,7,13), 24039.4, 24206.9, 24211.00, 13.24, 12.55, -1),
 (date(2026,7,14), 24141.0, 24211.0, 24052.05, 13.80, 13.24, -4),
]

V1 = dict(entry=2, flip=2, spread_vix=None, stop=0.30, target=1.50,
          target_spread=None, trail=None, gap_chase=None,
          highvix_entry=None, no_opposite=False, cooldown=False, size_cap=0.35)
V2 = dict(entry=2, flip=3, spread_vix=16.0, stop=0.35, target=1.50,
          target_spread=1.40, trail=1.25, gap_chase=0.009,
          highvix_entry=None, no_opposite=False, cooldown=False, size_cap=0.35)
V3 = dict(entry=2, flip=3, spread_vix=16.0, stop=0.35, target=1.50,
          target_spread=1.40, trail=1.25, gap_chase=0.009,
          highvix_entry=4, no_opposite=True, cooldown=False, size_cap=0.20)

def pick_expiry(d):
    for e in EXPIRIES:
        if (e - d).days >= 2:
            return e

def run(days, params, cash=100000.0, positions=None, log=None, curve=None, tag=""):
    positions = positions if positions is not None else []
    log = log if log is not None else []
    curve = curve if curve is not None else []

    def val(pos, spot, vix, d, ef=0.0):
        days_left = (pos["expiry"] - d).days + ef
        v = bs(spot, pos["strike"], vix, days_left, pos["type"])
        if pos.get("short_strike"):
            v -= bs(spot, pos["short_strike"], vix, days_left, pos["type"])
        return v

    def close_pos(pos, spot, vix, d, when, reason, ef=0.0):
        nonlocal cash
        m = val(pos, spot, vix, d, ef)
        legs = 2 if pos.get("short_strike") else 1
        proceeds = m * 0.985 * LOT - FEE * legs
        cash += proceeds
        pnl = proceeds - pos["cost"]
        log.append((d.isoformat(), when, f"EXIT {pos['desc']}", f"{m:.1f}pts", round(pnl), reason))
        positions.remove(pos)

    stopped_yesterday = [False]
    for d, o, pc, c, vixc, vixp, score in days:
        stopped_today = False
        tgt = lambda p: (params["target_spread"] if p.get("short_strike") and params["target_spread"] else params["target"])
        # morning
        for pos in positions[:]:
            m = val(pos, o, vixp, d, 0.25)
            if pos.get("trail_armed") and m <= pos["entry_v"]:
                close_pos(pos, o, vixp, d, "open", "trailing stop (breakeven)", 0.25); continue
            if abs(score) >= params["flip"] and ((score > 0) != (pos["type"] == "call")):
                close_pos(pos, o, vixp, d, "open", f"signal reversal ({score:+d})", 0.25); continue
            if m <= (1 - params["stop"]) * pos["entry_v"]:
                close_pos(pos, o, vixp, d, "open", f"stop -{int(params['stop']*100)}%", 0.25)
                stopped_today = True; continue
            if m >= tgt(pos) * pos["entry_v"]:
                close_pos(pos, o, vixp, d, "open", "target", 0.25); continue
            if params["trail"] and m >= params["trail"] * pos["entry_v"]:
                pos["trail_armed"] = True
        eff_entry = params["entry"]
        if params["highvix_entry"] and vixp > params["spread_vix"]:
            eff_entry = params["highvix_entry"]
        blocked = params["cooldown"] and (stopped_today or stopped_yesterday[0])
        if abs(score) >= eff_entry and not blocked:
            typ = "call" if score > 0 else "put"
            gap = (o - pc) / pc
            chase = params["gap_chase"] is not None and ((typ == "call" and gap > params["gap_chase"]) or (typ == "put" and gap < -params["gap_chase"]))
            opp = params["no_opposite"] and any(p["type"] != typ for p in positions)
            if chase:
                log.append((d.isoformat(), "open", f"SKIP {typ.upper()} entry", f"gap {gap*100:+.2f}%", "", "gap-chase filter"))
            elif opp:
                log.append((d.isoformat(), "open", f"SKIP {typ.upper()} entry", "", "", "opposite position held (no hedge-churn)"))
            elif not any(p["type"] == typ for p in positions) and len(positions) < 2:
                exp = pick_expiry(d)
                if exp:
                    strike = round(o / 50) * 50
                    dl = (exp - d).days + 0.25
                    v = bs(o, strike, vixp, dl, typ)
                    short_k = None
                    if params["spread_vix"] and vixp > params["spread_vix"]:
                        short_k = strike + 150 if typ == "call" else strike - 150
                        v -= bs(o, short_k, vixp, dl, typ)
                    legs = 2 if short_k else 1
                    cost = v * 1.015 * LOT + FEE * legs
                    eq_now = cash + sum(val(p, o, vixp, d, 0.25) * LOT for p in positions)
                    if cost <= params["size_cap"] * eq_now:
                        cash -= cost
                        desc = f"{typ.upper()} {strike}" + (f"/{short_k}" if short_k else "") + f" exp {exp.strftime('%d%b')}"
                        positions.append({"type": typ, "strike": strike, "short_strike": short_k,
                                          "expiry": exp, "entry_v": v, "cost": cost, "desc": desc})
                        log.append((d.isoformat(), "open", f"BUY {desc}", f"{v:.1f}pts Rs{cost:,.0f}", "", f"score {score:+d}"))
        # evening
        for pos in positions[:]:
            m = val(pos, c, vixc, d)
            if pos.get("trail_armed") and m <= pos["entry_v"]:
                close_pos(pos, c, vixc, d, "close", "trailing stop (breakeven)"); continue
            if m <= (1 - params["stop"]) * pos["entry_v"]:
                close_pos(pos, c, vixc, d, "close", f"stop -{int(params['stop']*100)}%")
                stopped_today = True; continue
            if m >= tgt(pos) * pos["entry_v"]:
                close_pos(pos, c, vixc, d, "close", "target"); continue
            if (pos["expiry"] - d).days <= 1:
                close_pos(pos, c, vixc, d, "close", "time stop"); continue
            if params["trail"] and m >= params["trail"] * pos["entry_v"]:
                pos["trail_armed"] = True
        eq = cash + sum(val(p, c, vixc, d) * LOT for p in positions)
        curve.append((d.isoformat(), round(eq)))
        stopped_yesterday[0] = stopped_today
    return cash, positions, log, curve

def report(name, log, curve):
    final = curve[-1][1]
    peak, mdd = 0, 0
    for _, e in curve:
        peak = max(peak, e); mdd = min(mdd, (e - peak) / peak)
    wins = sum(1 for r in log if r[4] != "" and r[4] > 0)
    losses = sum(1 for r in log if r[4] != "" and r[4] < 0)
    print(f"\n### {name}: final Rs {final:,} ({(final-100000)/1000:+.1f}%) | maxDD {mdd*100:.1f}% | W/L {wins}/{losses}")
    for r in log:
        print("  " + " | ".join(str(x) for x in r))

for name, days, params in [("v1 MAY (in-sample diagnosis)", MAY, V1),
                           ("v2 MAY (in-sample, tuned)", MAY, V2),
                           ("v1 JUN (reference)", JUN, V1),
                           ("v2 JUN (OUT-OF-SAMPLE)", JUN, V2),
                           ("v3 MAY (in-sample, both windows seen)", MAY, V3),
                           ("v3 JUN (in-sample, both windows seen)", JUN, V3)]:
    cash, pos, log, curve = run(days, params)
    report(name, log, curve)

print("\n" + "=" * 60)
cash, pos, log, curve = run(MAY, V1)
cash, pos, log, curve = run(JUN, V2, cash=cash, positions=pos, log=log, curve=curve)
report("FULL WALK-FORWARD May15->Jul14 (v1 then v2 from Jun 15)", log, curve)
print("\nEquity curve:")
for d, e in curve:
    print(f"  {d}  {e:,}")
