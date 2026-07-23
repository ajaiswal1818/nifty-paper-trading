#!/usr/bin/env python3
"""Reusable backtest engine for the paper-trading platform.

Data: engine/data/sessions_2026.csv (one row per session: OHLC-ish + VIX + the
morning sentiment score that was knowable pre-open) and engine/data/expiries.csv.

Params: a dict (see PRESETS, or any strategies/<id>/params.json).

Usage:
  python3 backtest.py v3                                  # preset, full data range
  python3 backtest.py v3 --from 2026-06-15 --to 2026-07-14
  python3 backtest.py ../strategies/v3-news-directional/params.json
  python3 backtest.py v1 --chain v2:2026-06-15            # walk-forward: switch params mid-run
Options: --capital N, --csv (machine-readable trade log), --quiet (summary only)
"""
import argparse, csv, json, math, os, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pricing import structure_value

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

DEFAULTS = dict(lot_size=75, fee_per_leg=100.0, entry_slippage=1.015,
                exit_slippage=0.985, max_positions=2, spread_width_pts=150,
                eod_exit=False)  # eod_exit: force-close everything at the close (intraday mode)

PRESETS = {
    "v1": dict(entry=2, flip=2, spread_vix=None, stop=0.30, target=1.50,
               target_spread=None, trail=None, gap_chase=None,
               highvix_entry=None, no_opposite=False, cooldown=False, size_cap=0.35),
    "v2": dict(entry=2, flip=3, spread_vix=16.0, stop=0.35, target=1.50,
               target_spread=1.40, trail=1.25, gap_chase=0.009,
               highvix_entry=None, no_opposite=False, cooldown=False, size_cap=0.35),
    "v3": dict(entry=2, flip=3, spread_vix=16.0, stop=0.35, target=1.50,
               target_spread=1.40, trail=1.25, gap_chase=0.009,
               highvix_entry=4, no_opposite=True, cooldown=False, size_cap=0.20),
}


def load_params(name_or_path):
    if name_or_path in PRESETS:
        return {**DEFAULTS, **PRESETS[name_or_path]}
    with open(name_or_path) as f:
        return {**DEFAULTS, **json.load(f)}


def load_sessions(start=None, end=None, data_file=None):
    rows = []
    path = data_file if data_file else os.path.join(DATA_DIR, "sessions_2026.csv")
    with open(path) as f:
        for r in csv.DictReader(f):
            d = date.fromisoformat(r["date"])
            if start and d < start:
                continue
            if end and d > end:
                continue
            rows.append((d, float(r["open"]), float(r["prev_close"]), float(r["close"]),
                         float(r["vix_close"]), float(r["vix_prev"]), int(r["morning_score"])))
    return rows


def load_expiries():
    with open(os.path.join(DATA_DIR, "expiries.csv")) as f:
        return [date.fromisoformat(r["expiry"]) for r in csv.DictReader(f)]


def run(days, params, cash=100000.0, positions=None, log=None, curve=None):
    """Simulate the rule set over sessions. Returns (cash, positions, log, curve).
    log rows: (date, when, action, detail, pnl_or_blank, reason)"""
    expiries = load_expiries()
    LOT, FEE = params["lot_size"], params["fee_per_leg"]
    positions = positions if positions is not None else []
    log = log if log is not None else []
    curve = curve if curve is not None else []

    def pick_expiry(d):
        # prefer a real expiry from the CSV within the next ~10 days (live data);
        # if the CSV doesn't cover this date (historical backtests), compute the
        # next weekly Thursday >= d+2 (NIFTY weekly expiry was Thursday 2019-2023).
        for e in expiries:
            if 2 <= (e - d).days <= 10:
                return e
        cand = d
        while (cand - d).days < 2 or cand.weekday() != 3:
            cand += timedelta(days=1)
        return cand

    def val(pos, spot, vix, d, ef=0.0):
        return structure_value(spot, pos["strike"], vix, (pos["expiry"] - d).days + ef,
                               pos["type"], pos.get("short_strike"))

    def close_pos(pos, spot, vix, d, when, reason, ef=0.0):
        nonlocal cash
        m = val(pos, spot, vix, d, ef)
        legs = 2 if pos.get("short_strike") else 1
        proceeds = m * params["exit_slippage"] * LOT - FEE * legs
        cash += proceeds
        pnl = proceeds - pos["cost"]
        log.append((d.isoformat(), when, f"EXIT {pos['desc']}", f"{m:.1f}pts", round(pnl), reason))
        positions.remove(pos)

    stopped_yesterday = [False]
    for d, o, pc, c, vixc, vixp, score in days:
        stopped_today = False
        tgt = lambda p: (params["target_spread"] if p.get("short_strike") and params["target_spread"] else params["target"])
        # ---- morning: manage open positions at the open ----
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
        # ---- morning: entry decision ----
        eff_entry = params["entry"]
        if params["highvix_entry"] and vixp > params["spread_vix"]:
            eff_entry = params["highvix_entry"]
        blocked = params["cooldown"] and (stopped_today or stopped_yesterday[0])
        if abs(score) >= eff_entry and not blocked:
            typ = "call" if score > 0 else "put"
            gap = (o - pc) / pc
            chase = params["gap_chase"] is not None and (
                (typ == "call" and gap > params["gap_chase"]) or (typ == "put" and gap < -params["gap_chase"]))
            opp = params["no_opposite"] and any(p["type"] != typ for p in positions)
            if chase:
                log.append((d.isoformat(), "open", f"SKIP {typ.upper()} entry", f"gap {gap*100:+.2f}%", "", "gap-chase filter"))
            elif opp:
                log.append((d.isoformat(), "open", f"SKIP {typ.upper()} entry", "", "", "opposite position held (no hedge-churn)"))
            elif not any(p["type"] == typ for p in positions) and len(positions) < params["max_positions"]:
                exp = pick_expiry(d)
                if exp:
                    strike = round(o / 50) * 50
                    dl = (exp - d).days + 0.25
                    short_k = None
                    if params["spread_vix"] and vixp > params["spread_vix"]:
                        short_k = strike + params["spread_width_pts"] if typ == "call" else strike - params["spread_width_pts"]
                    v = structure_value(o, strike, vixp, dl, typ, short_k)
                    legs = 2 if short_k else 1
                    cost = v * params["entry_slippage"] * LOT + FEE * legs
                    eq_now = cash + sum(val(p, o, vixp, d, 0.25) * LOT for p in positions)
                    if cost <= params["size_cap"] * eq_now:
                        cash -= cost
                        desc = f"{typ.upper()} {strike}" + (f"/{short_k}" if short_k else "") + f" exp {exp.strftime('%d%b')}"
                        positions.append({"type": typ, "strike": strike, "short_strike": short_k,
                                          "expiry": exp, "entry_v": v, "cost": cost, "desc": desc})
                        log.append((d.isoformat(), "open", f"BUY {desc}", f"{v:.1f}pts Rs{cost:,.0f}", "", f"score {score:+d}"))
        # ---- evening: manage at the close ----
        for pos in positions[:]:
            m = val(pos, c, vixc, d)
            if pos.get("trail_armed") and m <= pos["entry_v"]:
                close_pos(pos, c, vixc, d, "close", "trailing stop (breakeven)"); continue
            if m <= (1 - params["stop"]) * pos["entry_v"]:
                close_pos(pos, c, vixc, d, "close", f"stop -{int(params['stop']*100)}%")
                stopped_today = True; continue
            if m >= tgt(pos) * pos["entry_v"]:
                close_pos(pos, c, vixc, d, "close", "target"); continue
            if params["eod_exit"]:
                close_pos(pos, c, vixc, d, "close", "eod exit (intraday mode)"); continue
            if (pos["expiry"] - d).days <= 1:
                close_pos(pos, c, vixc, d, "close", "time stop"); continue
            if params["trail"] and m >= params["trail"] * pos["entry_v"]:
                pos["trail_armed"] = True
        eq = cash + sum(val(p, c, vixc, d) * LOT for p in positions)
        curve.append((d.isoformat(), round(eq)))
        stopped_yesterday[0] = stopped_today
    return cash, positions, log, curve


def report(name, log, curve, start_capital=100000, quiet=False):
    final = curve[-1][1] if curve else start_capital
    peak, mdd = 0, 0
    for _, e in curve:
        peak = max(peak, e); mdd = min(mdd, (e - peak) / peak)
    wins = sum(1 for r in log if r[4] != "" and r[4] > 0)
    losses = sum(1 for r in log if r[4] != "" and r[4] < 0)
    pct = (final - start_capital) / start_capital * 100
    print(f"\n### {name}: final Rs {final:,} ({pct:+.1f}%) | maxDD {mdd*100:.1f}% | W/L {wins}/{losses}")
    if not quiet:
        for r in log:
            print("  " + " | ".join(str(x) for x in r))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("params", help="preset name (v1|v2|v3) or path to a params.json")
    ap.add_argument("--from", dest="start", type=date.fromisoformat, default=None)
    ap.add_argument("--to", dest="end", type=date.fromisoformat, default=None)
    ap.add_argument("--capital", type=float, default=100000.0)
    ap.add_argument("--chain", default=None,
                    help="walk-forward switch, e.g. v2:2026-06-15 (new params from that date, capital carried)")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--data", default=None, help="path to an alternate sessions CSV (e.g. the reconstructed year)")
    a = ap.parse_args()

    sessions = load_sessions(a.start, a.end, a.data)
    if not sessions:
        sys.exit("no sessions in range")
    p1 = load_params(a.params)
    if a.chain:
        name2, cut = a.chain.split(":")
        cut = date.fromisoformat(cut)
        first = [s for s in sessions if s[0] < cut]
        second = [s for s in sessions if s[0] >= cut]
        cash, pos, log, curve = run(first, p1, cash=a.capital)
        cash, pos, log, curve = run(second, load_params(name2), cash=cash,
                                    positions=pos, log=log, curve=curve)
        report(f"{a.params} then {name2} from {cut}", log, curve, a.capital, a.quiet)
    else:
        cash, pos, log, curve = run(sessions, p1, cash=a.capital)
        rng = f"{sessions[0][0]} to {sessions[-1][0]}"
        report(f"{a.params} [{rng}]", log, curve, a.capital, a.quiet)


if __name__ == "__main__":
    main()
