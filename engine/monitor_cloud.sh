#!/bin/bash
# Cloud wrapper for the intraday monitor. Runs on an always-on Linux host
# (Oracle Cloud free VM) so exits are checked even when the Mac is off.
# Fired by cron every 5 min during market hours. PAPER ONLY.
#
# Design: the Mac's scheduled runs open positions and push. This wrapper pulls
# that state, runs one pure-python monitor pass, and pushes back ONLY when a
# trade actually fires. Mark-to-market passes keep state.json dirty locally so
# the trail-armed flag survives between passes; --autostash carries it across
# the next pull. When the Mac is off (the usual case) there is no contention.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
LOG="$REPO/engine/monitor_cloud.log"
ts() { TZ=Asia/Kolkata date '+%F %T'; }
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"

# keep the log from growing without bound
if [ -f "$LOG" ] && [ "$(wc -c <"$LOG")" -gt 500000 ]; then mv "$LOG" "$LOG.1"; fi

# 1. sync in the Mac's entries / latest state (reapply any local marks)
if ! git pull --rebase --autostash --quiet origin main 2>>"$LOG"; then
  echo "$(ts) pull/rebase failed; self-healing (discard local marks, re-pull)" >>"$LOG"
  git rebase --abort 2>/dev/null
  git checkout -- . 2>/dev/null
  git pull --rebase --quiet origin main 2>>"$LOG" || { echo "$(ts) pull still failing, skip pass" >>"$LOG"; exit 1; }
fi

# 2. one monitor pass (pure python; self-guards market hours/weekend/staleness)
/usr/bin/python3 "$REPO/engine/monitor.py" >>"$LOG" 2>&1

# 3. push ONLY when a trade fired (a trade_log.csv changed). Otherwise leave
#    the mark-only state.json change uncommitted for trail continuity.
if [ -n "$(git status --porcelain -- 'strategies/*/trade_log.csv')" ]; then
  git add -A
  git commit -q -m "cloud monitor: exit $(ts) IST"
  git pull --rebase --autostash --quiet origin main 2>>"$LOG"
  if git push --quiet origin main 2>>"$LOG"; then
    echo "$(ts) exit committed & pushed" >>"$LOG"
  else
    echo "$(ts) push failed, will retry next pass" >>"$LOG"
  fi
fi
