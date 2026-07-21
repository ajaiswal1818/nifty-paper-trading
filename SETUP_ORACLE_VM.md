# Deploy the intraday monitor on an Oracle Cloud free VM

Goal: run `engine/monitor.py` every 5 minutes on an always-on Linux box so exits are
checked even when your Mac is off. The VM becomes the SOLE monitor; the Mac keeps only
the scheduled entry/evening/night runs. PAPER ONLY, no real trades.

## 0. Before you start
The one real unknown is whether the VM can reach the Yahoo quote feed (some cloud IPs get
403s). Step 6 tests exactly that first. If it fails, tell me and I'll swap the data source
(NSE or another feed) before you finish wiring cron.

## 1. Create the VM (one time)
1. Sign up at cloud.oracle.com (Always Free tier; it asks for a card for identity only).
2. Compute → Instances → Create instance.
3. Image: **Ubuntu 22.04**. Shape: any **Always Free eligible** (VM.Standard.A1.Flex ARM,
   1 OCPU / 6 GB is plenty, or the E2.1.Micro).
4. Add your SSH public key (or let Oracle generate one and download the private key).
5. Create. Note the public IP.

## 2. Connect and install deps
```bash
ssh ubuntu@<PUBLIC_IP>
sudo apt update && sudo apt install -y git python3 tzdata
sudo timedatectl set-timezone Asia/Kolkata     # makes cron + logs read in IST
```

## 3. Give the VM write access to the repo (deploy key)
```bash
ssh-keygen -t ed25519 -C "oracle-monitor" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
```
Copy that line. On GitHub: repo **ajaiswal1818/nifty-paper-trading** → Settings → Deploy keys
→ Add deploy key → paste, **check "Allow write access"**, save.

## 4. Clone and set identity
```bash
cd ~
git clone git@github.com:ajaiswal1818/nifty-paper-trading.git
cd nifty-paper-trading
git config user.name "Oracle Monitor"
git config user.email "monitor@oracle.local"
chmod +x engine/monitor_cloud.sh engine/monitor.py
```

## 5. Confirm the monitor runs and can reach the data feed  ← the critical test
```bash
python3 engine/monitor.py --force
cat engine/monitor.log
```
- A clean run with no open positions prints nothing and exits 0 (that's success).
- If you see `quote fetch FAILED ... 403`, the VM can't reach Yahoo. **Stop and tell me**;
  I'll change the feed. Do not wire cron until this passes.
- To prove exits fire end-to-end, run a sandboxed simulation (no effect on real state):
```bash
cp -r ~/nifty-paper-trading /tmp/mt && cd /tmp/mt
python3 - <<'EOF'
import json,glob
for p in glob.glob('strategies/*/state.json'):
    s=json.load(open(p)); s['open_positions']=[{"trade_id":1,"option_type":"call","strike":24100,
    "expiry":"2026-07-28","lots":1,"lot_size":75,"entry_premium":160.0,"entry_cost_total":12280.0,
    "current_premium":160.0}]; s['cash']=87720.0; json.dump(s,open(p,'w'))
EOF
python3 engine/monitor.py --root /tmp/mt --spot 23600 --vix 15 --now 2026-07-28T13:00:00+05:30 --force
grep EXIT strategies/*/trade_log.csv && echo "exits work"; cd ~/nifty-paper-trading && rm -rf /tmp/mt
```

## 6. Schedule it
```bash
# edit the path in engine/monitor.cron if your clone isn't /home/ubuntu/nifty-paper-trading
crontab ~/nifty-paper-trading/engine/monitor.cron
crontab -l    # verify
```
Cron runs `monitor_cloud.sh` every 5 min, 09:00-15:59 IST, Mon-Fri. The script pulls the
Mac's latest state, runs one pass, and pushes back only when a trade actually fires.

## 7. Disable the Mac's local monitor (avoid double-exits)
On the **Mac**, unload the launchd monitor so only the VM manages exits:
```bash
launchctl unload ~/Library/LaunchAgents/com.nifty.monitor.plist
```
Keep the Mac's `com.nifty.gitsync` and the scheduled entry/evening/night tasks as they are.
(If the VM ever dies, you can re-load the Mac monitor as a manual backup, but never run both.)

## What each machine now owns
- **Oracle VM (always on):** intraday exit monitoring, 09:15-15:35 IST. Sole monitor.
- **Mac (when on):** morning entry decision (needs news judgment), evening mark + fallback
  EOD close, night plan, weekly research. If the Mac is off at 08:45, you simply miss that
  day's new entry; anything already open stays protected by the VM.

## Health checks
- VM: `tail ~/nifty-paper-trading/engine/monitor_cloud.log` and `engine/monitor.log`
  (a daily "heartbeat" line confirms the first market-hours pass each day).
- If `monitor_cloud.log` shows repeated pull/push failures, the deploy key or network needs
  a look. If `monitor.log` shows repeated quote failures, the feed is down.
