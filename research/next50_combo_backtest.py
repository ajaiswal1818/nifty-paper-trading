import json, subprocess, re
REPO="/sessions/elegant-busy-turing/mnt/Projects--nifty-paper-trading"
DATA=f"{REPO}/research/sessions_next50_signals.csv"
BASE={"version":"x","entry":2,"flip":3,"spread_vix":16.0,"stop":0.35,"target":1.5,
"target_spread":1.4,"trail":1.25,"gap_chase":0.009,"highvix_entry":4,"no_opposite":True,
"cooldown":False,"size_cap":0.35,"lot_size":25,"fee_per_leg":100.0,"entry_slippage":1.03,
"exit_slippage":0.97,"max_positions":2,"spread_width_pts":150,"eod_exit":True}
CFG={
"A_v3i_next50_base(e2,eod)":{},
"B_e3_eod":{"entry":3,"eod_exit":True},
"C_e3_hold_v3exits":{"entry":3,"eod_exit":False},
"D_e3_hold_fliponly(USER)":{"entry":3,"eod_exit":False,"stop":1.0,"target":99.0,"trail":None},
"E_e3_hold_flip+stop35":{"entry":3,"eod_exit":False,"target":99.0,"trail":None},
}
WIN={"2019-23":["--to","2023-12-31"],"2026oos":["--from","2026-01-01"]}
for name,over in CFG.items():
    p={**BASE,**over}; f="/sessions/elegant-busy-turing/mnt/outputs/sweep/c.json"; json.dump(p,open(f,"w"))
    out=[]
    for w,args in WIN.items():
        r=subprocess.run(["python3",f"{REPO}/engine/backtest.py",f,"--quiet","--data",DATA]+args,capture_output=True,text=True).stdout
        m=re.search(r"final Rs ([\d,]+) \(([+-][\d.]+)%\) \| maxDD (-?[\d.]+)% \| W/L (\d+)/(\d+)",r)
        out.append(f"{w}: Rs{m.group(1)} ({m.group(2)}%) DD{m.group(3)}% W/L {m.group(4)}/{m.group(5)}" if m else f"{w}: PARSE FAIL {r[:100]}")
    print(name," || ".join(out))
