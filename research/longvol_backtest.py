#!/usr/bin/env python3
import csv, math, datetime as dt

# ---- Black-Scholes (copied verbatim from engine/pricing.py) ----
def norm_cdf(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
def bs_price(spot,strike,iv,days,opt,r=0.065,q=0.012):
    t=max(days,0.25)/365.0; s=iv/100.0
    d1=(math.log(spot/strike)+(r-q+s*s/2)*t)/(s*math.sqrt(t)); d2=d1-s*math.sqrt(t)
    if opt=="call": return spot*math.exp(-q*t)*norm_cdf(d1)-strike*math.exp(-r*t)*norm_cdf(d2)
    return strike*math.exp(-r*t)*norm_cdf(-d2)-spot*math.exp(-q*t)*norm_cdf(-d1)

LOT=75; FEE_LEG=100.0; ENT_SLIP=1.015; EXT_SLIP=0.985

rows=[]
with open("sessions_2026.csv") as f:
    for r in csv.DictReader(f):
        rows.append(dict(date=dt.date.fromisoformat(r["date"]),
                         open=float(r["open"]),prev_close=float(r["prev_close"]),
                         close=float(r["close"]),vix_close=float(r["vix_close"]),
                         vix_prev=float(r["vix_prev"]),score=int(r["morning_score"])))

def next_weekly_expiry(d):
    # NIFTY weekly expiry = Tuesday. Pick first Tuesday strictly > d+1 (skip today/tomorrow).
    cand=d+dt.timedelta(days=2)
    while cand.weekday()!=1:  # Monday=0, Tuesday=1
        cand+=dt.timedelta(days=1)
    return cand

def atm(x): return round(x/50.0)*50

def straddle_val(spot,K,iv,days):
    return bs_price(spot,K,iv,days,"call")+bs_price(spot,K,iv,days,"put")

def run(vix_max=99, hold=1, lots=1, target=None, stop=None, gap_max=None, label=""):
    """Enter ATM straddle at open when vix_prev<=vix_max (and |open gap|<=gap_max if set).
       IV at entry = vix_prev (knowable pre-open). Exit at close after `hold` sessions,
       or earlier if intraday-close mark hits target/stop. Mark-to-close uses vix_close."""
    cap=100000.0; eq=cap; peak=cap; maxdd=0.0; trades=[]
    i=0; n=len(rows)
    while i<n:
        s=rows[i]
        gap=abs(s["open"]/s["prev_close"]-1)
        if s["vix_prev"]<=vix_max and (gap_max is None or gap<=gap_max):
            K=atm(s["open"]); exp=next_weekly_expiry(s["date"])
            d0=(exp-s["date"]).days
            entry_pts=straddle_val(s["open"],K,s["vix_prev"],d0)
            entry_cost=entry_pts*ENT_SLIP*LOT*lots + FEE_LEG*2*lots
            # walk forward up to `hold` sessions, checking close each day
            exit_i=min(i+hold-1,n-1); reason="time"
            if target or stop:
                for j in range(i,min(i+hold,n)):
                    sj=rows[j]; dj=(exp-sj["date"]).days
                    if dj<0: exit_i=j; reason="expiry"; break
                    val=straddle_val(sj["close"],K,sj["vix_close"],dj)
                    ret=val/entry_pts-1
                    if target and ret>=target: exit_i=j; reason="target"; break
                    if stop and ret<=-stop: exit_i=j; reason="stop"; break
                    exit_i=j
            sx=rows[exit_i]; dx=max((exp-sx["date"]).days,0)
            exit_pts=straddle_val(sx["close"],K,sx["vix_close"],dx)
            exit_val=exit_pts*EXT_SLIP*LOT*lots - FEE_LEG*2*lots
            pnl=exit_val-entry_cost
            eq+=pnl
            peak=max(peak,eq); maxdd=min(maxdd,eq/peak-1)
            trades.append((s["date"],pnl,reason,entry_cost))
            i=exit_i+1
        else:
            i+=1
    if not trades:
        print(f"{label:38s} NO TRADES"); return
    wins=[t[1] for t in trades if t[1]>0]; losses=[t[1] for t in trades if t[1]<=0]
    tot=eq-cap
    aw=sum(wins)/len(wins) if wins else 0
    al=sum(losses)/len(losses) if losses else 0
    best=max(trades,key=lambda t:t[1]); worst=min(trades,key=lambda t:t[1])
    print(f"{label:38s} ret {tot/cap*100:+6.1f}%  N={len(trades):2d}  win {len(wins)/len(trades)*100:3.0f}%  "
          f"avgW {aw:+6.0f} avgL {al:+6.0f}  maxDD {maxdd*100:5.1f}%  best {best[1]:+6.0f}({best[0]}) worst {worst[1]:+6.0f}({worst[0]})")
    return tot

print("="*150)
print("LONG-VOLATILITY (ATM STRADDLE) BACKTEST  |  May15-Jul27 2026  |  50 sessions  |  cap Rs100,000  |  friction=platform model")
print("="*150)
print("\n-- A. Buy vol every session (baseline, no event filter) --")
run(hold=1,lots=1,label="every session, hold 1d, 1 lot")
run(hold=2,lots=1,label="every session, hold 2d, 1 lot")

print("\n-- B. Buy CHEAP vol only (vix_prev filter = the 'vol is cheap pre-event' thesis) --")
for vx in (13.5,13.0,12.5):
    run(vix_max=vx,hold=1,lots=1,label=f"vix_prev<={vx}, hold 1d, 1 lot")
for vx in (13.5,13.0,12.5):
    run(vix_max=vx,hold=2,lots=1,label=f"vix_prev<={vx}, hold 2d, 1 lot")

print("\n-- C. Cheap vol + flat open (buy vol not direction: |gap|<=0.3%) --")
run(vix_max=13.0,hold=2,lots=1,gap_max=0.003,label="vix<=13 & gap<=0.3%, hold 2d, 1 lot")
run(vix_max=12.5,hold=2,lots=1,gap_max=0.003,label="vix<=12.5 & gap<=0.3%, hold 2d, 1 lot")

print("\n-- D. Best filter + target/stop management --")
run(vix_max=13.0,hold=3,lots=1,target=0.40,stop=0.30,label="vix<=13, hold<=3d, +40/-30, 1 lot")
run(vix_max=12.5,hold=3,lots=1,target=0.40,stop=0.30,label="vix<=12.5, hold<=3d, +40/-30, 1 lot")

print("\n-- E. Sizing up (2 lots) on the cleaner filters --")
run(vix_max=13.0,hold=1,lots=2,label="vix<=13, hold 1d, 2 lots")
run(vix_max=12.5,hold=2,lots=2,label="vix<=12.5, hold 2d, 2 lots")
run(vix_max=13.0,hold=3,lots=2,target=0.40,stop=0.30,label="vix<=13, hold<=3d, +40/-30, 2 lots")

print("\n"+"="*150)
print("VERIFICATION: winner variant (vix_prev<=13, hold 1d same-day-close exit) trade-by-trade, 1 lot")
print("="*150)
def run_verbose(vix_max,hold,lots):
    cap=100000.0; eq=cap; T=[]
    for s in rows:
        if s["vix_prev"]<=vix_max:
            K=atm(s["open"]); exp=next_weekly_expiry(s["date"]); d0=(exp-s["date"]).days
            ent=straddle_val(s["open"],K,s["vix_prev"],d0)*ENT_SLIP*LOT*lots+FEE_LEG*2*lots
            dx=max((exp-s["date"]).days,0)
            ex=straddle_val(s["close"],K,s["vix_close"],dx)*EXT_SLIP*LOT*lots-FEE_LEG*2*lots
            pnl=ex-ent; eq+=pnl
            move=(s["close"]/s["open"]-1)*100
            T.append(pnl)
            print(f"  {s['date']}  K={K}  vixP={s['vix_prev']:5.2f}  daymove {move:+5.2f}%  P&L {pnl:+8.0f}  eq {eq:9.0f}")
    tot=eq-cap
    print(f"  TOTAL {tot:+.0f} ({tot/cap*100:+.1f}%)  N={len(T)}")
    T.sort()
    print(f"  ex-best-trade: {(sum(T)-T[-1]):+.0f}   ex-best-2: {(sum(T)-T[-1]-T[-2]):+.0f}")
    return tot
run_verbose(13.0,1,1)
