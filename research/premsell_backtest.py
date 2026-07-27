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
            vix_close=float(r["vix_close"]),vix_prev=float(r["vix_prev"]),score=int(r["morning_score"])))
def next_weekly_expiry(d):
    c=d+dt.timedelta(days=2)
    while c.weekday()!=1: c+=dt.timedelta(days=1)
    return c
def atm(x): return round(x/50.0)*50

# straddle daily P&L (for correlation), same rule as winner: vix<=13, same-day close, 1 lot
def straddle_pnl(s):
    K=atm(s["open"]); exp=next_weekly_expiry(s["date"]); d0=(exp-s["date"]).days
    ent=(bs_price(s["open"],K,s["vix_prev"],d0,"call")+bs_price(s["open"],K,s["vix_prev"],d0,"put"))*ENT_SLIP*LOT+FEE_LEG*2
    dx=max((exp-s["date"]).days,0)
    ex=(bs_price(s["close"],K,s["vix_close"],dx,"call")+bs_price(s["close"],K,s["vix_close"],dx,"put"))*EXT_SLIP*LOT-FEE_LEG*2
    return ex-ent

def run_condor(offset=250, wing=150, vix_min=0, hold=1, lots=1, condor=True, label=""):
    """SELL OTM call@K+off & put@K-off at open; if condor also BUY wings at +/-(off+wing).
       Exit same-day close. Short: receive prem*EXT_SLIP, pay back prem*ENT_SLIP."""
    cap=100000.0; eq=cap; peak=cap; maxdd=0.0; T=[]; days=[]
    for s in rows:
        if s["vix_prev"]<vix_min: continue
        K=atm(s["open"]); exp=next_weekly_expiry(s["date"]); d0=(exp-s["date"]).days
        cs,ps=K+offset,K-offset
        legs_credit=bs_price(s["open"],cs,s["vix_prev"],d0,"call")+bs_price(s["open"],ps,s["vix_prev"],d0,"put")
        legs_debit=0.0; nlegs=2
        if condor:
            cl,pl=K+offset+wing,K-offset-wing
            legs_debit=bs_price(s["open"],cl,s["vix_prev"],d0,"call")+bs_price(s["open"],pl,s["vix_prev"],d0,"put")
            nlegs=4
        credit=(legs_credit*EXT_SLIP-legs_debit*ENT_SLIP)*LOT*lots - FEE_LEG*nlegs*lots
        dx=max((exp-s["date"]).days,0)
        legs_credit_x=bs_price(s["close"],cs,s["vix_close"],dx,"call")+bs_price(s["close"],ps,s["vix_close"],dx,"put")
        legs_debit_x=0.0
        if condor:
            legs_debit_x=bs_price(s["close"],cl,s["vix_close"],dx,"call")+bs_price(s["close"],pl,s["vix_close"],dx,"put")
        buyback=(legs_credit_x*ENT_SLIP-legs_debit_x*EXT_SLIP)*LOT*lots + FEE_LEG*nlegs*lots
        pnl=credit-buyback
        eq+=pnl; peak=max(peak,eq); maxdd=min(maxdd,eq/peak-1); T.append(pnl); days.append(s)
    if not T: print(f"{label:44s} NO TRADES"); return
    w=[x for x in T if x>0]; tot=eq-cap
    best=max(range(len(T)),key=lambda i:T[i]); worst=min(range(len(T)),key=lambda i:T[i])
    # correlation with straddle on same days
    sp=[straddle_pnl(s) for s in days]
    n=len(T); mt=sum(T)/n; ms=sum(sp)/n
    cov=sum((T[i]-mt)*(sp[i]-ms) for i in range(n))/n
    vt=(sum((x-mt)**2 for x in T)/n)**.5; vs=(sum((x-ms)**2 for x in sp)/n)**.5
    corr=cov/(vt*vs) if vt*vs else 0
    print(f"{label:44s} ret {tot/cap*100:+6.1f}% N={n:2d} win {len(w)/n*100:3.0f}% "
          f"maxDD {maxdd*100:5.1f}% best {T[best]:+6.0f}({days[best]['date']}) worst {T[worst]:+6.0f}({days[worst]['date']}) corr_w/straddle {corr:+.2f}")

print("="*150)
print("PREMIUM-SELLING BACKTEST (sell at open, buy back same-day close) | May15-Jul27 2026 | cap Rs100,000")
print("="*150)
print("\n-- Short strangle (undefined risk) --")
run_condor(offset=250,condor=False,label="strangle 250 OTM, all sessions, 1 lot")
run_condor(offset=300,condor=False,label="strangle 300 OTM, all sessions, 1 lot")
run_condor(offset=250,condor=False,vix_min=13,label="strangle 250 OTM, vix_prev>=13, 1 lot")
print("\n-- Iron condor (defined risk: sell 250 OTM, buy 150 wings) --")
run_condor(offset=250,wing=150,condor=True,label="condor 250/400, all sessions, 1 lot")
run_condor(offset=300,wing=150,condor=True,label="condor 300/450, all sessions, 1 lot")
run_condor(offset=250,wing=150,condor=True,vix_min=13,label="condor 250/400, vix_prev>=13, 1 lot")
run_condor(offset=200,wing=150,condor=True,label="condor 200/350, all sessions, 1 lot")
print("\n-- Sizing up the cleanest condor --")
run_condor(offset=250,wing=150,condor=True,lots=2,label="condor 250/400, all sessions, 2 lots")
