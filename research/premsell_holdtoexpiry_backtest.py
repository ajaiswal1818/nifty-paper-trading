#!/usr/bin/env python3
import csv, math, datetime as dt
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
        rows.append(dict(date=dt.date.fromisoformat(r["date"]),open=float(r["open"]),
            prev_close=float(r["prev_close"]),close=float(r["close"]),
            vix_close=float(r["vix_close"]),vix_prev=float(r["vix_prev"])))
def nwe(d):
    c=d+dt.timedelta(days=2)
    while c.weekday()!=1: c+=dt.timedelta(days=1)
    return c
def atm(x): return round(x/50.0)*50
def val(spot,cs,ps,iv,days,cl=None,pl=None):
    v=bs_price(spot,cs,iv,days,"call")+bs_price(spot,ps,iv,days,"put")
    if cl: v-=bs_price(spot,cl,iv,days,"call")+bs_price(spot,pl,iv,days,"put")
    return v
def intrinsic(spot,cs,ps,cl=None,pl=None):
    v=max(spot-cs,0)+max(ps-spot,0)
    if cl: v-=max(spot-cl,0)+max(pl-spot,0)
    return v

def run(offset,wing,dte_max,vix_min=0,vix_max=99,lots=1,stop_mult=None,label=""):
    """Sell condor when flat & days_to_expiry<=dte_max & vix in band. Hold to expiry (settle intrinsic).
       Optional stop: buy back if structure value >= stop_mult * entry_credit_pts (loss control)."""
    cap=100000.0; eq=cap; peak=cap; maxdd=0.0; T=[]
    i=0; n=len(rows)
    while i<n:
        s=rows[i]; exp=nwe(s["date"]); d0=(exp-s["date"]).days
        if not(vix_min<=s["vix_prev"]<=vix_max and 2<=d0<=dte_max):
            i+=1; continue
        K=atm(s["open"]); cs,ps=K+offset,K-offset
        cl,pl=(K+offset+wing,K-offset-wing) if wing else (None,None)
        entry_pts=val(s["open"],cs,ps,s["vix_prev"],d0,cl,pl)
        credit=entry_pts*EXT_SLIP*LOT*lots - FEE_LEG*(4 if wing else 2)*lots
        # walk to expiry
        j=i; exit_pts=None
        while j<n and rows[j]["date"]<exp:
            sj=rows[j]; dj=(exp-sj["date"]).days
            cur=val(sj["close"],cs,ps,sj["vix_close"],dj,cl,pl)
            if stop_mult and cur>=stop_mult*entry_pts:
                exit_pts=cur; break
            j+=1
        if exit_pts is None:
            # settle at expiry-day close intrinsic (or last available)
            k=j if j<n else n-1
            exit_pts=intrinsic(rows[k]["close"],cs,ps,cl,pl)
        buyback=exit_pts*ENT_SLIP*LOT*lots + FEE_LEG*(4 if wing else 2)*lots
        pnl=credit-buyback; eq+=pnl; peak=max(peak,eq); maxdd=min(maxdd,eq/peak-1); T.append((s["date"],pnl))
        i=j+1 if j>i else i+1
    if not T: print(f"{label:46s} NO TRADES"); return
    w=[p for _,p in T if p>0]; tot=eq-cap
    b=max(T,key=lambda x:x[1]); wo=min(T,key=lambda x:x[1])
    print(f"{label:46s} ret {tot/cap*100:+6.1f}% N={len(T):2d} win {len(w)/len(T)*100:3.0f}% "
          f"maxDD {maxdd*100:6.1f}% best {b[1]:+6.0f}({b[0]}) worst {wo[1]:+7.0f}({wo[0]})")

print("="*140)
print("PREMIUM-SELLING v2: SELL & HOLD TO EXPIRY | May15-Jul27 2026 | cap Rs100,000")
print("="*140)
print("\n-- Iron condor, hold to expiry, no stop --")
run(250,150,6,label="condor 250/400, dte<=6, no stop, 1 lot")
run(300,150,6,label="condor 300/450, dte<=6, no stop, 1 lot")
run(300,150,4,label="condor 300/450, dte<=4, no stop, 1 lot")
print("\n-- Iron condor + loss stop (buy back at 2x credit) --")
run(250,150,6,stop_mult=2.0,label="condor 250/400, dte<=6, stop@2x, 1 lot")
run(300,150,6,stop_mult=2.0,label="condor 300/450, dte<=6, stop@2x, 1 lot")
run(300,150,6,stop_mult=2.5,label="condor 300/450, dte<=6, stop@2.5x, 1 lot")
print("\n-- Condor + AVOID low-vix (only sell when premium richer) --")
run(300,150,6,vix_min=13,stop_mult=2.0,label="condor 300/450, vix>=13, stop@2x, 1 lot")
run(300,150,6,vix_max=13,stop_mult=2.0,label="condor 300/450, vix<=13, stop@2x, 1 lot")
print("\n-- Short strangle, hold to expiry + stop --")
run(300,0,6,stop_mult=2.0,label="strangle 300, dte<=6, stop@2x, 1 lot")
run(350,0,6,stop_mult=2.0,label="strangle 350, dte<=6, stop@2x, 1 lot")
