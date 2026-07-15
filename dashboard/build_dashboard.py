#!/usr/bin/env python3
"""Regenerates dashboard/dashboard.html from strategies/registry.json.
Self-contained output (inline SVG, no JS/CDN) so it opens offline in any browser.
Run from anywhere: python3 dashboard/build_dashboard.py
"""
import csv, html, json, os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "dashboard", "dashboard.html")


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def inr(x):
    return f"₹{x:,.0f}"


def svg_equity(curve, start_capital, w=860, h=240):
    """curve: list of (label, equity). Inline SVG line chart with baseline."""
    if len(curve) < 2:
        return "<p class='muted'>Not enough equity points yet to chart.</p>"
    vals = [v for _, v in curve]
    lo, hi = min(vals + [start_capital]), max(vals + [start_capital])
    pad = max((hi - lo) * 0.1, 1)
    lo, hi = lo - pad, hi + pad
    px, py = 46, 18
    iw, ih = w - px - 12, h - py - 30
    X = lambda i: px + iw * i / (len(vals) - 1)
    Y = lambda v: py + ih * (1 - (v - lo) / (hi - lo))
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
    base_y = Y(start_capital)
    color = "#0a7d38" if vals[-1] >= start_capital else "#c0392b"
    gl = []
    for i in range(5):
        gv = lo + (hi - lo) * i / 4
        gy = Y(gv)
        gl.append(f"<line x1='{px}' y1='{gy:.1f}' x2='{w-12}' y2='{gy:.1f}' stroke='#e8e8e3' stroke-width='1'/>"
                  f"<text x='{px-6}' y='{gy+4:.1f}' font-size='10' fill='#8a8a83' text-anchor='end'>{gv/1000:.0f}k</text>")
    n = len(curve)
    lab_idx = sorted({0, n // 2, n - 1})
    labels = "".join(f"<text x='{X(i):.1f}' y='{h-8}' font-size='10' fill='#8a8a83' text-anchor='middle'>{html.escape(str(curve[i][0])[:16])}</text>"
                     for i in lab_idx)
    return (f"<svg viewBox='0 0 {w} {h}' role='img' style='width:100%;height:auto'>"
            + "".join(gl)
            + f"<line x1='{px}' y1='{base_y:.1f}' x2='{w-12}' y2='{base_y:.1f}' stroke='#b0b0a8' stroke-dasharray='4 4' stroke-width='1'/>"
            + f"<polyline points='{pts}' fill='none' stroke='{color}' stroke-width='2'/>"
            + f"<circle cx='{X(len(vals)-1):.1f}' cy='{Y(vals[-1]):.1f}' r='3.5' fill='{color}'/>"
            + labels + "</svg>")


def table(rows, cols, empty_msg, limit=None):
    if not rows:
        return f"<p class='muted'>{empty_msg}</p>"
    shown = rows[-limit:] if limit else rows
    head = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
    body = ""
    for r in reversed(shown):
        body += "<tr>" + "".join(f"<td>{html.escape(str(r.get(c, '')))}</td>" for c in cols) + "</tr>"
    note = f"<p class='muted'>Showing last {len(shown)} of {len(rows)}.</p>" if limit and len(rows) > limit else ""
    return f"<div class='twrap'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>{note}"


def strategy_section(s):
    sdir = os.path.join(ROOT, "strategies", s["id"])
    files = s.get("files", {})
    state = {}
    sp = os.path.join(sdir, files.get("state", "state.json"))
    if os.path.exists(sp):
        with open(sp) as f:
            state = json.load(f)
    start = s.get("capital_start", state.get("starting_capital", 100000))
    eq = state.get("total_equity", start)
    pnl = eq - start
    pct = pnl / start * 100
    cls = "pos" if pnl >= 0 else "neg"
    snap = state.get("market_snapshot", {})
    curve_rows = read_csv(os.path.join(sdir, files.get("equity_curve", "equity_curve.csv")))
    curve = [(r.get("datetime_ist", r.get("date", "")), float(r["total_equity"]))
             for r in curve_rows if r.get("total_equity")]
    trades = read_csv(os.path.join(sdir, files.get("trade_log", "trade_log.csv")))
    positions = state.get("open_positions", [])
    pos_rows = [{
        "id": p.get("trade_id", ""), "type": p.get("option_type", ""),
        "strike": (f"{p.get('strike','')}/{p['short_strike']}" if p.get("short_strike") else p.get("strike", "")),
        "expiry": p.get("expiry", ""), "lots": p.get("lots", 1),
        "entry": p.get("entry_premium", ""), "mark": p.get("current_premium", ""),
    } for p in positions]
    plan = state.get("pending_plan") or {}
    plan_html = ""
    if plan:
        news = "".join(f"<li>{html.escape(k)}</li>" for k in plan.get("key_news", [])[:3])
        plan_html = (f"<div class='plan'><b>Pending plan</b> · bias {html.escape(str(plan.get('bias','?')))} "
                     f"(draft {plan.get('score_draft','?')}) · written {html.escape(str(plan.get('written_at',''))[:16])}"
                     f"<ul>{news}</ul></div>")
    realized = state.get("realized_pnl", 0)
    unreal = state.get("unrealized_pnl", 0)
    n_closed = sum(1 for t in trades if str(t.get("realized_pnl", "")).strip() not in ("", "0", "0.0"))
    return f"""
<section class='card'>
  <div class='shead'>
    <div>
      <h2>{html.escape(s.get('name', s['id']))}</h2>
      <span class='badge {html.escape(s.get('status','active'))}'>{html.escape(s.get('status','active'))}</span>
      <span class='badge mode'>{html.escape(s.get('mode','paper'))}</span>
      <span class='muted'>since {html.escape(str(s.get('started','')))}</span>
    </div>
    <div class='thenumber {cls}'>{inr(eq)}<small>{'+' if pnl>=0 else ''}{inr(pnl).replace('₹','₹') } ({pct:+.1f}%)</small></div>
  </div>
  <div class='stats'>
    <div><b>{inr(state.get('cash', start))}</b><span>cash</span></div>
    <div><b>{inr(realized)}</b><span>realized P&L</span></div>
    <div><b>{inr(unreal)}</b><span>unrealized P&L</span></div>
    <div><b>{len(positions)}</b><span>open positions</span></div>
    <div><b>{n_closed}</b><span>closed trades</span></div>
    <div><b>{html.escape(str(state.get('last_run',''))[:16])}</b><span>last run</span></div>
  </div>
  {svg_equity(curve, start)}
  <h3>Open positions</h3>
  {table(pos_rows, ["id","type","strike","expiry","lots","entry","mark"], "No open positions.")}
  {plan_html}
  <h3>Trade log</h3>
  {table(trades, ["datetime_ist","action","option_type","strike","expiry","premium","reason","sentiment_score","realized_pnl"], "No trades yet. The first live morning run makes the first entry decision.", limit=15)}
</section>"""


def main():
    with open(os.path.join(ROOT, "strategies", "registry.json")) as f:
        reg = json.load(f)
    snap_line = ""
    for s in reg["strategies"]:
        sp = os.path.join(ROOT, "strategies", s["id"], "state.json")
        if os.path.exists(sp):
            with open(sp) as f:
                snap = json.load(f).get("market_snapshot", {})
            if snap:
                snap_line = (f"NIFTY {snap.get('nifty_spot','?')} · VIX {snap.get('india_vix','?')} · "
                             f"PCR {snap.get('pcr','?')} · FII {snap.get('fii_net_cash_cr','?')} Cr · as of {snap.get('as_of','?')}")
                break
    sections = "".join(strategy_section(s) for s in reg["strategies"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    page = f"""<!DOCTYPE html>
<html lang='en'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Paper trading dashboard</title>
<style>
 body{{font:14px/1.5 -apple-system,'Segoe UI',sans-serif;background:#f4f4ef;color:#1a1a17;margin:0;padding:24px}}
 h1{{font-size:20px;margin:0 0 2px}} h2{{font-size:16px;margin:0;display:inline}} h3{{font-size:13px;margin:18px 0 6px;text-transform:uppercase;letter-spacing:.04em;color:#6b6b64}}
 .muted{{color:#8a8a83;font-size:12px}}
 .card{{background:#fff;border:1px solid #e4e4dd;border-radius:10px;padding:18px 20px;margin-top:16px;max-width:920px}}
 .shead{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}}
 .badge{{display:inline-block;font-size:11px;padding:1px 8px;border-radius:99px;margin-left:6px;border:1px solid #ccc;vertical-align:2px}}
 .badge.active{{background:#e7f5ec;border-color:#9fd4b2;color:#0a7d38}}
 .badge.paused{{background:#fdf3e0;border-color:#e6c98a;color:#9a6b00}}
 .badge.retired{{background:#f0f0ec;color:#8a8a83}}
 .badge.mode{{background:#eef3fb;border-color:#b9cdEE;color:#2b5aa5}}
 .thenumber{{text-align:right;font-size:26px;font-weight:700}}
 .thenumber small{{display:block;font-size:13px;font-weight:600}}
 .pos{{color:#0a7d38}} .neg{{color:#c0392b}}
 .stats{{display:flex;gap:22px;flex-wrap:wrap;margin:12px 0 14px}}
 .stats div{{min-width:90px}} .stats b{{display:block;font-size:15px}} .stats span{{font-size:11px;color:#8a8a83}}
 .twrap{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:12.5px}}
 th,td{{text-align:left;padding:5px 10px 5px 0;border-bottom:1px solid #eeeee8;white-space:nowrap}}
 th{{color:#8a8a83;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.03em}}
 .plan{{background:#fafaf5;border:1px solid #ecece4;border-radius:8px;padding:10px 14px;font-size:12.5px;margin-top:14px}}
 .plan ul{{margin:6px 0 0 16px;padding:0}}
 header .warn{{color:#9a6b00;font-size:12px}}
</style></head><body>
<header>
 <h1>Paper trading dashboard</h1>
 <div class='muted'>{html.escape(snap_line)}</div>
 <div class='warn'>Paper trading only. All fills simulated. Generated {now} by dashboard/build_dashboard.py.</div>
</header>
{sections}
</body></html>"""
    with open(OUT, "w") as f:
        f.write(page)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
