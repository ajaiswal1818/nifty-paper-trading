#!/bin/bash
# Cloud wrapper for the intraday monitor. Runs on the always-on VM via cron.
# PAPER ONLY.
#
# Sync model (robust): each pass HARD-RESETS to the latest pushed state before
# running, so the VM never holds local uncommitted edits that could conflict with
# the Mac's pushes. It commits+pushes when a trade fires OR when a position's
# breakeven-trail arms (so that memory survives the next reset). Stop / target /
# EOD exits key off the committed entry price and are always reliable; committing
# on arm keeps the breakeven-trail reliable too. Plain mark-to-market passes
# (nothing fired, nothing armed) are discarded on the next reset -- no conflicts.
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

# 3. push when a trade fired (trade_log changed) OR a breakeven-trail is armed
#    (so the arm persists across the next reset). During market hours the Mac
#    runs no scheduled jobs, so these commits don't collide with it.
if [ -n "$(git status --porcelain -- 'strategies/*/trade_log.csv')" ] \
   || grep -lq '"trail_armed": *true' strategies/*/state.json 2>/dev/null; then
  git add -A
  git commit -q -m "cloud monitor: exit $(ts) IST"
  git fetch --quiet origin main && git rebase --quiet origin/main 2>>"$LOG"
  if git push --quiet origin main 2>>"$LOG"; then
    echo "$(ts) exit committed & pushed" >>"$LOG"
  else
    echo "$(ts) push failed; discarding on next pass and retrying" >>"$LOG"
  fi
fi
