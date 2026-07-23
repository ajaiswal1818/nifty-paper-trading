#!/usr/bin/env python3
"""Assemble ~1-2 years of daily sessions for backtesting v3/v3i, with the entry
score reconstructed from the signals we can get WITHOUT hindsight.

Reconstructed signals (per strategies/.../STRATEGY.md):
  gap  = (open - prev_close)/prev_close : +1 >+0.3%, -1 <-0.3%   [proxy for GIFT]
  us   = S&P 500 prior-session % change : +1 >+0.5%, -1 <-0.5%
  fii  = FII net cash (Cr), prior day   : +1 >+1000, -1 <-1000
  pcr  = NIFTY PCR, prior day close     : +1 >1.2,  -1 <0.8
News (the 5th signal) is OMITTED: it cannot be scored a year back without hindsight.

RUN THIS ON THE VM (Yahoo is reachable there; the sandbox blocks it).

Prices/VIX/US: fetched automatically from Yahoo (stdlib only).
FII and PCR: read from optional local CSVs so we never depend on a fragile scraper:
  research/fii_history.csv   with header: date,fii_net_cr      (date = YYYY-MM-DD)
  research/pcr_history.csv   with header: date,pcr
If a CSV is missing, that signal is treated as 0 and the day is flagged in the
coverage report, so you always see exactly what the score is built from.

Outputs:
  engine/data/sessions_history.csv  -> 7-col schema the backtest engine reads
  research/history_signals.csv      -> full detail (each component) for auditing
Then: python3 engine/backtest.py <params> --data engine/data/sessions_history.csv
"""
import argparse, csv, json, os, sys, urllib.parse, urllib.request
from datetime import datetime, date, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RANGE = "2y"  # default when no explicit --start/--end given

# set by main() from --start/--end; when present, fetch that exact window
PERIOD1 = None
PERIOD2 = None


def yahoo_daily(symbol):
    """Return {date: {'open':o,'close':c}} from Yahoo chart API (daily).
    Uses an explicit period1/period2 window if set, else the default range."""
    base = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?interval=1d"
    if PERIOD1 and PERIOD2:
        url = f"{base}&period1={PERIOD1}&period2={PERIOD2}"
    else:
        url = f"{base}&range={RANGE}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    r = d["chart"]["result"][0]
    ts = r["timestamp"]
    q = r["indicators"]["quote"][0]
    out = {}
    for i, t in enumerate(ts):
        dt = datetime.fromtimestamp(t, tz=timezone.utc).date()
        o, c = q["open"][i], q["close"][i]
        if o is None or c is None:
            continue
        out[dt] = {"open": float(o), "close": float(c)}
    return out


def load_optional_csv(path, valcol):
    """{date: float} from an optional 2-col csv; {} if absent."""
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        return {}
    out = {}
    with open(p) as f:
        for row in csv.DictReader(f):
            try:
                out[date.fromisoformat(row["date"].strip())] = float(row[valcol])
            except (ValueError, KeyError):
                continue
    return out


def sig(v, hi, lo):
    if v is None:
        return 0
    return 1 if v > hi else (-1 if v < lo else 0)


def prior_value(sorted_dates, series, d):
    """Most recent series value strictly before date d (for US close, FII, PCR)."""
    prev = None
    for dt in sorted_dates:
        if dt < d:
            prev = series[dt]
        else:
            break
    return prev


def main():
    global PERIOD1, PERIOD2
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=date.fromisoformat, default=None, help="YYYY-MM-DD (else last 2y)")
    ap.add_argument("--end", type=date.fromisoformat, default=None)
    a = ap.parse_args()
    if a.start and a.end:
        PERIOD1 = int(datetime(a.start.year, a.start.month, a.start.day, tzinfo=timezone.utc).timestamp())
        PERIOD2 = int(datetime(a.end.year, a.end.month, a.end.day, tzinfo=timezone.utc).timestamp()) + 86400
        print(f"Window: {a.start} -> {a.end}")
    print("Fetching NIFTY (^NSEI), S&P 500 (^GSPC), India VIX (^INDIAVIX) from Yahoo...")
    nse = yahoo_daily("^NSEI")
    gspc = yahoo_daily("^GSPC")
    vix = yahoo_daily("^INDIAVIX")
    fii = load_optional_csv("research/fii_history.csv", "fii_net_cr")
    pcr = load_optional_csv("research/pcr_history.csv", "pcr")
    print(f"  NIFTY days={len(nse)}  S&P days={len(gspc)}  VIX days={len(vix)}  "
          f"FII rows={len(fii)}  PCR rows={len(pcr)}")

    ndates = sorted(nse)
    gspc_dates = sorted(gspc)
    gspc_pct = {}
    gd = sorted(gspc)
    for i in range(1, len(gd)):
        gspc_pct[gd[i]] = (gspc[gd[i]]["close"] - gspc[gd[i-1]]["close"]) / gspc[gd[i-1]]["close"] * 100
    gpct_dates = sorted(gspc_pct)
    fii_dates, pcr_dates = sorted(fii), sorted(pcr)

    rows, cov = [], {"gap": 0, "us": 0, "fii": 0, "pcr": 0, "total": 0}
    for i in range(1, len(ndates)):
        d, pd = ndates[i], ndates[i-1]
        o, c = nse[d]["open"], nse[d]["close"]
        pc = nse[pd]["close"]
        vc = vix.get(d, {}).get("close")
        vp = vix.get(pd, {}).get("close")
        if vc is None or vp is None:
            continue
        gap = (o - pc) / pc * 100
        us = prior_value(gpct_dates, gspc_pct, d)
        fv = prior_value(fii_dates, fii, d) if fii else None
        pv = prior_value(pcr_dates, pcr, d) if pcr else None
        sg, su = sig(gap, 0.3, -0.3), sig(us, 0.5, -0.5)
        sf = sig(fv, 1000, -1000) if fv is not None else 0
        sp = sig(pv, 1.2, 0.8) if pv is not None else 0
        score = sg + su + sf + sp
        if fv is not None:
            cov["fii"] += 1
        if pv is not None:
            cov["pcr"] += 1
        cov["gap"] += 1
        cov["us"] += 1 if us is not None else 0
        cov["total"] += 1
        rows.append(dict(date=d.isoformat(), open=round(o, 2), prev_close=round(pc, 2),
                         close=round(c, 2), vix_close=round(vc, 2), vix_prev=round(vp, 2),
                         gap_pct=round(gap, 3), us_pct=(round(us, 3) if us is not None else ""),
                         fii_net=(fv if fv is not None else ""),
                         pcr=(pv if pv is not None else ""),
                         sig_gap=sg, sig_us=su, sig_fii=sf, sig_pcr=sp, morning_score=score))

    os.makedirs(os.path.join(ROOT, "engine", "data"), exist_ok=True)
    sess = os.path.join(ROOT, "engine", "data", "sessions_history.csv")
    with open(sess, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "open", "prev_close", "close", "vix_close", "vix_prev", "morning_score"])
        for r in rows:
            w.writerow([r["date"], r["open"], r["prev_close"], r["close"],
                        r["vix_close"], r["vix_prev"], r["morning_score"]])
    detail = os.path.join(ROOT, "research", "history_signals.csv")
    with open(detail, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    n = cov["total"]
    print(f"\nAssembled {n} sessions: {rows[0]['date']} -> {rows[-1]['date']}")
    print("Signal coverage (days with real data, not defaulted to 0):")
    for k in ("gap", "us", "fii", "pcr"):
        pct = 100 * cov[k] / n if n else 0
        note = "" if cov[k] == n else "  <-- gaps: missing days scored 0 (neutral)"
        print(f"  {k:4}: {cov[k]:4}/{n} ({pct:5.1f}%){note}")
    if not fii:
        print("  NOTE: research/fii_history.csv not found -> FII signal is all 0.")
    if not pcr:
        print("  NOTE: research/pcr_history.csv not found -> PCR signal is all 0.")
    print(f"\nWrote {sess}\n      {detail}")
    print("Backtest:  python3 engine/backtest.py v3 --data engine/data/sessions_history.csv")


if __name__ == "__main__":
    main()
