#!/usr/bin/env python3
"""Intraday exit monitor for the paper-trading platform. PAPER ONLY.

Fired by launchd every 5 minutes (see engine/com.nifty.monitor.plist).
Each invocation is one pass:
  1. Guard: weekday, 09:15-15:35 IST, lock not held, fresh quotes.
  2. Fetch NIFTY spot (^NSEI) and India VIX (^INDIAVIX) from Yahoo (stdlib only).
  3. For every active strategy with open positions: reprice (Black-Scholes),
     execute mechanical exits (breakeven trail, stop, target, and EOD close for
     eod_exit strategies from 15:20), update state/trade_log/equity_curve.
  4. Regenerate the dashboard if anything closed.

Entries are NEVER made here - entries need news judgment and belong to the
scheduled morning run. This script is pure arithmetic.

Test flags: --spot/--vix (skip fetch), --now ISO_TS (fake clock),
            --root DIR (sandbox state), --force (ignore market-hours guard)
"""
import argparse, csv, json, os, subprocess, sys, urllib.parse, urllib.request
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pricing import structure_value

IST = ZoneInfo("Asia/Kolkata")
LOG_MAX = 500_000


def log(root, msg):
    path = os.path.join(root, "engine", "monitor.log")
    try:
        if os.path.exists(path) and os.path.getsize(path) > LOG_MAX:
            os.rename(path, path + ".1")
    except OSError:
        pass
    with open(path, "a") as f:
        f.write(f"{datetime.now(IST).isoformat(timespec='seconds')} {msg}\n")


def fetch_quote(symbol):
    """Return (price, quote_unix_time) from Yahoo chart API. Raises on failure."""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(symbol)}?interval=5m&range=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=15))
    meta = d["chart"]["result"][0]["meta"]
    return float(meta["regularMarketPrice"]), int(meta["regularMarketTime"])


def days_to_expiry(expiry, now):
    """Calendar days with an intraday fraction consistent with the backtest
    convention (open = +0.25, close = +0.0)."""
    d = (expiry - now.date()).days
    close_t = now.replace(hour=15, minute=30, second=0, microsecond=0)
    frac = max(0.0, min(1.0, (close_t - now).total_seconds() / (6.25 * 3600))) * 0.25
    return d + frac


def take_lock(root):
    path = os.path.join(root, ".monitor.lock")
    try:
        st = os.stat(path)
        if datetime.now().timestamp() - st.st_mtime > 180:
            os.remove(path)  # stale
        else:
            return None
    except FileNotFoundError:
        pass
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode()); os.close(fd)
        return path
    except FileExistsError:
        return None


def close_position(root, sid, strat_dir, state, pos, value, spot, vix, now, reason, params):
    lot, lots = pos.get("lot_size", 75), pos.get("lots", 1)
    legs = 2 if pos.get("short_strike") else 1
    fee = params.get("fee_per_leg", 100.0) * legs
    if pos.get("side") == "short":
        # Net-short structure (e.g. iron-condor side): buy back to close (pay).
        # entry_cost_total is stored NEGATIVE for shorts (the credit was a cash inflow
        # at entry). P&L = credit_received - buyback_cost.
        txn = value * params.get("entry_slippage", 1.015) * lot * lots + fee  # buyback cost
        pnl = (-pos["entry_cost_total"]) - txn
        cash_delta = -txn
    else:
        txn = value * params.get("exit_slippage", 0.985) * lot * lots - fee   # sale proceeds
        pnl = txn - pos["entry_cost_total"]
        cash_delta = txn
    state["cash"] = round(state["cash"] + cash_delta, 2)
    state["realized_pnl"] = round(state.get("realized_pnl", 0) + pnl, 2)
    state["open_positions"].remove(pos)
    strike_txt = (f"{pos['strike']}/{pos['short_strike']}" if pos.get("short_strike") else str(pos["strike"]))
    with open(os.path.join(strat_dir, "trade_log.csv"), "a", newline="") as f:
        csv.writer(f).writerow([
            pos.get("trade_id", ""), "EXIT", now.strftime("%Y-%m-%d %H:%M"), "NIFTY",
            strike_txt, pos.get("expiry", ""), pos.get("option_type", ""), lots, lot,
            f"{value:.2f}", f"{txn:.2f}", f"{fee:.0f}",
            f"monitor: {reason}", "", spot, vix, f"{pnl:.2f}"])
    log(root, f"[{sid}] EXIT {pos.get('option_type','?').upper()} {strike_txt} "
              f"@ {value:.1f}pts pnl {pnl:+,.0f} ({reason})")
    return pnl


def process_strategy(root, entry, spots, vix, now):
    sid = entry["id"]
    strat_dir = os.path.join(root, "strategies", sid)
    with open(os.path.join(strat_dir, "params.json")) as f:
        params = json.load(f)
    sp = os.path.join(strat_dir, "state.json")
    with open(sp) as f:
        state = json.load(f)
    positions = state.get("open_positions", [])
    underlying = params.get("underlying", "NIFTY")   # NIFTY | NIFTYNXT50
    spot = spots.get(underlying)
    if spot is None:
        log(root, f"[{sid}] no spot for {underlying}; skipping")
        return 0, len(positions)
    closed = 0
    eod_now = params.get("eod_exit") and (now.hour, now.minute) >= (15, 20)
    for pos in positions[:]:
        d = date.fromisoformat(pos["expiry"])
        value = structure_value(spot, pos["strike"], vix, days_to_expiry(d, now),
                                pos["option_type"], pos.get("short_strike"))
        entry_v = pos["entry_premium"]
        is_spread = bool(pos.get("short_strike"))
        reason = None
        if pos.get("side") == "short":
            # Net-short: loss grows as the structure gets MORE expensive to buy back;
            # profit as it decays. Stop/target are inverted vs a long position.
            stop_mult = params.get("stop_mult", 2.0)       # buy back if value >= N x credit
            tgt_cap = params.get("target_capture", 0.5)    # buy back after capturing X of credit
            expiry_now = (params.get("expiry_exit") and now.date() >= d
                          and (now.hour, now.minute) >= (15, 20))
            if value >= stop_mult * entry_v:
                reason = f"stop {stop_mult:g}x credit"
            elif value <= (1 - tgt_cap) * entry_v:
                reason = f"target {int(tgt_cap*100)}% capture"
            elif expiry_now:
                reason = "expiry close"
            elif eod_now:
                reason = "eod exit (intraday mode)"
        else:
            target = (params.get("target_spread") or params["target"]) if is_spread else params["target"]
            if pos.get("trail_armed") and value <= entry_v:
                reason = "trailing stop (breakeven)"
            elif value <= (1 - params["stop"]) * entry_v:
                reason = f"stop -{int(params['stop']*100)}%"
            elif value >= target * entry_v:
                reason = "target"
            elif eod_now:
                reason = "eod exit (intraday mode)"
        if reason:
            close_position(root, sid, strat_dir, state, pos, value, spot, vix, now, reason, params)
            closed += 1
            continue
        if pos.get("side") != "short" and params.get("trail") and value >= params["trail"] * entry_v:
            pos["trail_armed"] = True
        pos["current_premium"] = round(value, 2)
    # MTM: a long position adds its mark to equity; a short position is a liability
    # (subtract its current buyback value) and profits when the mark falls below entry.
    def _sgn(p):
        return -1 if p.get("side") == "short" else 1
    unreal = sum(_sgn(p) * (p["current_premium"] - p["entry_premium"]) * p.get("lot_size", 75) * p.get("lots", 1)
                 for p in state.get("open_positions", []))
    marks = sum(_sgn(p) * p["current_premium"] * p.get("lot_size", 75) * p.get("lots", 1)
                for p in state.get("open_positions", []))
    state["unrealized_pnl"] = round(unreal, 2)
    state["total_equity"] = round(state["cash"] + marks, 2)
    state["last_monitor"] = now.isoformat(timespec="seconds")
    if closed:
        with open(os.path.join(strat_dir, "equity_curve.csv"), "a", newline="") as f:
            csv.writer(f).writerow([now.strftime("%Y-%m-%d %H:%M"), "monitor-exit", spot, vix,
                                    state["cash"], state["unrealized_pnl"], state["total_equity"],
                                    len(state["open_positions"])])
    with open(sp, "w") as f:
        json.dump(state, f, indent=2)
    return closed, len(state.get("open_positions", []))


def main():
    ap = argparse.ArgumentParser()
    default_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--root", default=default_root)
    ap.add_argument("--spot", type=float, default=None)
    ap.add_argument("--vix", type=float, default=None)
    ap.add_argument("--now", default=None, help="ISO timestamp override for testing")
    ap.add_argument("--force", action="store_true", help="skip market-hours/staleness guards")
    a = ap.parse_args()
    root = a.root
    now = datetime.fromisoformat(a.now).astimezone(IST) if a.now else datetime.now(IST)

    if not a.force:
        if now.weekday() >= 5:
            return  # weekend, silent
        if not ((9, 15) <= (now.hour, now.minute) <= (15, 35)):
            return  # outside market hours, silent

    lock = take_lock(root)
    if not lock:
        log(root, "skip: lock held (scheduled run or another monitor pass active)")
        return
    try:
        # daily heartbeat: one log line on the first market-hours pass of each day,
        # so "is the monitor alive?" is answerable from engine/monitor.log
        hb = os.path.join(root, "engine", ".monitor.heartbeat")
        today = now.date().isoformat()
        try:
            prev = open(hb).read().strip()
        except OSError:
            prev = ""
        if prev != today:
            with open(hb, "w") as f:
                f.write(today)
            log(root, f"heartbeat: monitor alive, first market-hours pass of {today}")

        with open(os.path.join(root, "strategies", "registry.json")) as f:
            reg = json.load(f)
        active = [s for s in reg["strategies"] if s.get("status") == "active"]
        have_pos = []
        for s in active:
            sp = os.path.join(root, "strategies", s["id"], "state.json")
            with open(sp) as f:
                if json.load(f).get("open_positions"):
                    have_pos.append(s)
        if not have_pos:
            return  # nothing to watch; stay silent to keep the log readable

        # which underlyings do the open positions actually need?
        SYMBOL = {"NIFTY": "^NSEI", "NIFTYNXT50": "^NSMIDCP"}
        needed = set()
        for s in have_pos:
            with open(os.path.join(root, "strategies", s["id"], "params.json")) as f:
                needed.add(json.load(f).get("underlying", "NIFTY"))
        spots, vix = {}, a.vix
        if a.spot is not None:
            for u in needed:
                spots[u] = a.spot  # test override applies to all needed underlyings
        else:
            try:
                for u in needed:
                    q, t_q = fetch_quote(SYMBOL[u])
                    if not a.force and now.timestamp() - t_q > 900:
                        log(root, f"skip: {u} quote stale ({int(now.timestamp()-t_q)}s), market likely closed")
                        return
                    spots[u] = q
                if vix is None:
                    vix, _ = fetch_quote("^INDIAVIX")
            except Exception as e:
                log(root, f"quote fetch FAILED: {type(e).__name__} {e}")
                return

        total_closed = 0
        for s in have_pos:
            closed, remaining = process_strategy(root, s, spots, vix, now)
            total_closed += closed
        if total_closed:
            subprocess.run([sys.executable, os.path.join(root, "dashboard", "build_dashboard.py")],
                           check=False, capture_output=True)
            log(root, f"pass done: spots {spots} vix {vix}, {total_closed} exit(s), dashboard rebuilt")
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass


if __name__ == "__main__":
    main()
