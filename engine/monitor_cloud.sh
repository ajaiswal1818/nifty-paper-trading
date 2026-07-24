#!/bin/bash
# Cloud wrapper for the intraday monitor. Runs on the always-on VM via cron.
# PAPER ONLY.
#
# Sync model (robust): each pass HARD-RESETS to the latest pushed state before
# running, so the VM never holds local uncommitted edits that could conflict with
# the Mac's pushes. It commits+pushes ONLY when a trade actually fires. Trade-off:
# intraday mark-to-market and the breakeven-trail arm are not persisted between
# passes on the VM; stop / target / EOD exits (which key off the committed
# entry price) are fully reliable, and the 18:00 evening run re-checks the trail
# against the close as a backstop.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
LOG="$REPO/engine/monitor_cloud.log"
ts() { TZ=Asia/Kolkata date '+%F %T'; }
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new"

if [ -f "$LOG" ] && [ "$(wc -c <"$LOG")" -gt 500000 ]; then mv "$LOG" "$LOG.1"; fi

# 1. align exactly to the latest pushed state. Clears any half-finished
#    merge/rebase and discards local marks -> no pull conflicts, ever.
git rebase --abort 2>/dev/null
git merge --abort 2>/dev/null
if ! git fetch --quiet origin main 2>>"$LOG"; then
  echo "$(ts) fetch failed, skip pass" >>"$LOG"; exit 1
fi
git reset --hard --quiet origin/main 2>>"$LOG"

# 2. one monitor pass (pure python; self-guards market hours/weekend/staleness)
/usr/bin/python3 "$REPO/engine/monitor.py" >>"$LOG" 2>&1

# 3. push ONLY when a trade fired (a trade_log.csv changed).
if [ -n "$(git status --porcelain -- 'strategies/*/trade_log.csv')" ]; then
  git add -A
  git commit -q -m "cloud monitor: exit $(ts) IST"
  git fetch --quiet origin main && git rebase --quiet origin/main 2>>"$LOG"
  if git push --quiet origin main 2>>"$LOG"; then
    echo "$(ts) exit committed & pushed" >>"$LOG"
  else
    echo "$(ts) push failed; discarding on next pass and retrying" >>"$LOG"
  fi
fi
