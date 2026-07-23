#!/bin/bash
# Host-side git sync for the paper-trading platform. Fired by launchd
# (com.nifty.gitsync.plist) every 15 minutes. Safe to run any time.
#
# Commits whatever the runs/monitor changed, then rebases on the remote and
# pushes. Cowork sessions cannot push (no SSH keys in the sandbox), so this
# script is the only thing that talks to the remote from this machine.
set -u
cd "$(dirname "$0")/.." || exit 1

# clear stale locks first: sandbox sessions can't always delete them.
# >10 min old means no live operation owns it (sessions/monitor finish in seconds).
find .git/index.lock .git/HEAD.lock .monitor.lock -maxdepth 0 -mmin +10 -delete 2>/dev/null
# leftover temp objects from interrupted commits (harmless but accumulate)
find .git/objects -name 'tmp_obj_*' -mmin +60 -delete 2>/dev/null

# never fight a live git operation (a Cowork session may be committing)
[ -f .git/index.lock ] && exit 0
[ -f .git/HEAD.lock ] && exit 0

git add -A
if ! git diff --cached --quiet; then
    git commit -m "auto-sync: $(date '+%Y-%m-%d %H:%M')" --quiet
fi

# only sync if a remote is configured
git remote get-url origin >/dev/null 2>&1 || exit 0
git pull --rebase --autostash --quiet origin main || exit 1
git push --quiet origin main
