#!/bin/bash
# Cloud wrapper for the intraday monitor. Runs on the always-on VM via cron.
# PAPER ONLY.
#
# Sync model (robust): each pass HARD-RESETS to the latest pushed state before
# running, so the VM never holds local uncommitted edits that could conflict with
# the Mac's pushes. It commits+pushes when a trade fires OR when a position's
# breakeven-trail NEWLY arms (so that memory survives the next reset). Stop /
# target / EOD exits key off the committed entry price and are always reliable;
# committing on arm keeps the breakeven-trail reliable too. Plain mark-to-market
# passes (nothing fired, nothing newly armed) are discarded on the next reset --
# no conflicts.
#
# The arm test is an EDGE, not a level (fixed 2026-08-04). It compares the armed
# set before the pass -- which, thanks to the hard reset above, IS the committed
# state -- against the armed set after. Testing the level instead (`grep
# trail_armed.*true`) matched on every subsequent pass while a position stayed
# armed, producing one empty mark-to-market commit every 5 minutes: 48 such
# commits on 2026-08-03 alone, all mislabelled "exit". See DECISIONS.md.
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

# signature of every position currently carrying an armed breakeven-trail.
# Parsed as JSON so it is immune to indentation/key-order changes in state.json.
armed_sig() {
  /usr/bin/python3 - <<'PY' 2>/dev/null || echo "SIGFAIL"
import glob, json
out = []
for path in sorted(glob.glob("strategies/*/state.json")):
    try:
        state = json.load(open(path))
    except Exception:
        out.append(path + "#unreadable")
        continue
    for pos in state.get("open_positions", []):
        if pos.get("trail_armed"):
            out.append("%s#%s" % (path, pos.get("trade_id")))
print(",".join(out))
PY
}

# 2. one monitor pass (pure python; self-guards market hours/weekend/staleness)
ARMED_BEFORE="$(armed_sig)"
/usr/bin/python3 "$REPO/engine/monitor.py" >>"$LOG" 2>&1
ARMED_AFTER="$(armed_sig)"

# 3. push when a trade fired (trade_log changed) OR the armed set CHANGED this
#    pass (so a new arm persists across the next reset). An unchanged armed set
#    is already committed -- committing again would only write mark-to-market
#    noise. During market hours the Mac runs no scheduled jobs, so these commits
#    don't collide with it.
if [ -n "$(git status --porcelain -- 'strategies/*/trade_log.csv')" ]; then
  REASON="exit"
elif [ "$ARMED_AFTER" != "$ARMED_BEFORE" ]; then
  REASON="trail armed"
else
  REASON=""
fi

if [ -n "$REASON" ]; then
  git add -A
  git commit -q -m "cloud monitor: $REASON $(ts) IST"
  git fetch --quiet origin main && git rebase --quiet origin/main 2>>"$LOG"
  if git push --quiet origin main 2>>"$LOG"; then
    echo "$(ts) $REASON committed & pushed" >>"$LOG"
  else
    echo "$(ts) push failed; discarding on next pass and retrying" >>"$LOG"
  fi
fi
