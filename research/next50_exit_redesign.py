import json, subprocess, re
REPO="/sessions/elegant-busy-turing/mnt/Projects--nifty-paper-trading"
DATA=f"{REPO}/research/sessions_next50_signals.csv"
PRIMARY={"version":"v3h2-next50","entry":3,"flip":3,"spread_vix":16.0,
 "stop":0.35,"target":99.0,"target_spread":None,"trail":None,
 "gap_chase":0.009,"highvix_entry":4,"no_opposite":True,"cooldown":False,
 "size_cap":0.35,"lot_size":25,"fee_per_leg":100.0,"entry_slippage":1.03,
 "exit_slippage":0.97,"max_positions":2,"spread_width_pts":150,"eod_exit":False,
 "underlying":"NIFTYNXT50","expiries_file":"expiries_next50.csv",
 "decay_exit":True,"decay_level":1,"max_hold":5,"expiry_buffer":7}
VAR={
 "PRIMARY decay(1)+hold5+stop35+buf7":{},
 "  sens: decay_level 3 (strict)":{"decay_level":3},
 "  sens: max_hold 3":{"max_hold":3},
 "  sens: max_hold 10":{"max_hold":10},
 "  sens: no max_hold":{"max_hold":None},
 "  sens: expiry_buffer 1":{"expiry_buffer":1},
 "  sens: no stop":{"stop":1.0},
 "  sens: no decay (flip only)":{"decay_exit":False},
 "  sens: +target 1.5":{"target":1.5},
}
W={"2019-23":["--to","2023-12-31"],"2026 OOS":["--from","2026-01-01"]}
for name,over in VAR.items():
    p={**PRIMARY,**over}; f="/sessions/elegant-busy-turing/mnt/outputs/sweep/r.json"; json.dump(p,open(f,"w"))
    cells=[]
    for w,a in W.items():
        out=subprocess.run(["python3",f"{REPO}/engine/backtest.py",f,"--quiet","--data",DATA]+a,capture_output=True,text=True).stdout
        m=re.search(r"final Rs ([\d,]+) \(([+-][\d.]+)%\) \| maxDD (-?[\d.]+)% \| W/L (\d+)/(\d+)",out)
        cells.append(f"{w}: {m.group(2):>6}% DD{m.group(3):>6}% W/L {m.group(4)}/{m.group(5)}" if m else f"{w}: FAIL")
    print(f"{name:36s} " + " | ".join(cells))
