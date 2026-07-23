#!/usr/bin/env python3
"""Short-premium research backtest: defined-risk short iron condor. PAPER ONLY.

Hypothesis (opposite of v3): in calm, range-bound markets, COLLECTING theta beats
paying it. On low-VIX days with no strong directional signal, sell an out-of-the-money
call spread AND put spread (a short iron condor), keep the net credit if NIFTY stays
in the range, with loss capped by the wings (defined risk, never naked).

Entry (one position at a time):
  vix_prev < VIX_MAX  and  |morning_score| <= SCORE_MAX  and  a weekly expiry >= 2 days out.
Structure at the open (ATM = open):
  sell call ~+2%, buy call ~+3% (wing);  sell put ~-2%, buy put ~-3% (wing).
  credit C = call-spread value + put-spread value (what we receive).
Exit:
  profit target: captured >= PT_FRAC of C   |  stop: loss >= STOP_FRAC of C
  time: close at the weekly expiry.
P&L per position (index points): received C at entry, pay V to close -> C - V.

Usage: python3 research/backtest_shortvol.py [--data engine/data/sessions_history.csv]
                                             [--vixmax 15] [--scoremax 1] [--quiet]
Shares engine/pricing.py. Research only; not wired into the live platform.
"""
import argparse, csv, os, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine"))
from pricing import structure_value

DEFAULTS = dict(vix_max=15.0, score_max=1, lot=75, fee_leg=100.0,
                short_call=1.02, long_call=1.03, short_put=0.98, long_put=0.97,
                pt_frac=0.50, stop_frac=1.0, entry_slip=1.015, exit_slip=0.985)


def next_thursday(d):
    c = d
    while (c - d).days < 2 or c.weekday() != 3:
        c += timedelta(days=1)
    return c


def condor_value(spot, iv, days, k):
    """Cost to close the condor = call-spread value + put-spread value (index points)."""
    call = structure_value(spot, k["sc"], iv, days, "call", k["lc"])
    put = structure_value(spot, k["sp"], iv, days, "put", k["lp"])
    return call + put


def load(path, start, end):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            d = date.fromisoformat(r["date"])
            if (start and d < start) or (end and d > end):
                continue
            rows.append((d, float(r["open"]), float(r["close"]),
                         float(r["vix_close"]), float(r["vix_prev"]), int(r["morning_score"])))
    return rows


def run(days, p, cash=100000.0):
    LOT, FEE = p["lot"], p["fee_leg"]
    pos = None
    log, curve = [], []
    for d, o, c, vixc, vixp, score in days:
        # manage open position at the close
        if pos:
            V = condor_value(c, vixc, (pos["exp"] - d).days, pos["k"]) * p["entry_slip"]
            pnl = pos["credit"] - V  # points
            reason = None
            if pnl >= p["pt_frac"] * pos["credit"]:
                reason = f"profit target ({int(p['pt_frac']*100)}% of credit)"
            elif pnl <= -p["stop_frac"] * pos["credit"]:
                reason = f"stop (-{int(p['stop_frac']*100)}% of credit)"
            elif (pos["exp"] - d).days <= 0:
                reason = "expiry"
            if reason:
                cash -= V * LOT + 4 * FEE  # 4 legs to close
                realized = (pos["credit"] * LOT) - (V * LOT) - 8 * FEE  # 4 legs open + 4 close
                log.append((d.isoformat(), "CLOSE", f"{realized:+.0f}", reason))
                pos = None
        # entry at the open
        if pos is None and vixp < p["vix_max"] and abs(score) <= p["score_max"]:
            exp = next_thursday(d)
            dte = (exp - d).days
            if dte >= 2:
                k = {"sc": round(o*p["short_call"]/50)*50, "lc": round(o*p["long_call"]/50)*50,
                     "sp": round(o*p["short_put"]/50)*50, "lp": round(o*p["long_put"]/50)*50}
                credit = condor_value(o, vixp, dte, k) * p["exit_slip"]
                width = (k["lc"] - k["sc"]) + (k["sp"] - k["lp"])  # total defined risk span (pts)
                if credit > 0:
                    cash += credit * LOT - 4 * FEE  # receive credit; 4 legs at entry
                    pos = {"exp": exp, "k": k, "credit": credit, "entry": d, "width": width}
                    log.append((d.isoformat(), "OPEN",
                                f"IC {k['sp']}/{k['sc']} +{credit:.0f}pts", f"vix {vixp:.1f} score {score}"))
        # mark equity
        if pos:
            V = condor_value(c, vixc, (pos["exp"] - d).days, pos["k"]) * p["entry_slip"]
            eq = cash - V * LOT
        else:
            eq = cash
        curve.append((d.isoformat(), round(eq)))
    return cash, log, curve


def report(name, log, curve, cap=100000):
    final = curve[-1][1] if curve else cap
    peak = mdd = 0
    for _, e in curve:
        peak = max(peak, e); mdd = min(mdd, (e - peak) / peak if peak else 0)
    closes = [r for r in log if r[1] == "CLOSE"]
    wins = sum(1 for r in closes if float(r[2]) > 0)
    losses = sum(1 for r in closes if float(r[2]) <= 0)
    print(f"\n### {name}: final Rs {final:,} ({(final-cap)/cap*100:+.1f}%) | "
          f"maxDD {mdd*100:.1f}% | trades {len(closes)} | W/L {wins}/{losses}")
    return final


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(root, "engine/data/sessions_history.csv"))
    ap.add_argument("--from", dest="start", type=date.fromisoformat, default=None)
    ap.add_argument("--to", dest="end", type=date.fromisoformat, default=None)
    ap.add_argument("--vixmax", type=float, default=None)
    ap.add_argument("--scoremax", type=int, default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    p = dict(DEFAULTS)
    if a.vixmax is not None: p["vix_max"] = a.vixmax
    if a.scoremax is not None: p["score_max"] = a.scoremax
    days = load(a.data, a.start, a.end)
    if not days:
        sys.exit("no sessions")
    cash, log, curve = run(days, p)
    report(f"short-IC [{days[0][0]} to {days[-1][0]}] vixmax {p['vix_max']} scoremax {p['score_max']}",
           log, curve)
    if not a.quiet:
        for r in log:
            print("  " + " | ".join(str(x) for x in r))


if __name__ == "__main__":
    main()
