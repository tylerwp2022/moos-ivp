#!/bin/bash
# Claude Code Stop hook: a scratch fleet left running on the 9100 ports
# (a MOOSDB whose working directory is one of Claude's scratch folders,
# the session scratchpad under /tmp/claude-* or a chat test run under
# test/runs/) blocks the turn from ending, with a reason that names the
# folder, until it is shut down or the reply says why it stays up. The
# user's own missions on 9000, or anything not started from a scratch
# folder, never trigger it. A fleet still in use passes too: fleet.sh up
# and the chat test driver write the PID of the script that owns the
# fleet to <folder>/.driver, and while that process is alive the fleet
# is a test in progress, not a leftover (a test killed mid-way leaves a
# dead PID and is caught). Silent and exit 0 otherwise. Reads the
# hook's JSON on stdin only to see stop_hook_active: after one block the
# model has had its say, so a second stop goes through.
input=$(cat 2>/dev/null)
case "$input" in
  *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) exit 0;;
esac
found=""
for pid in $(ss -ltnp 2>/dev/null | grep -E ':910[0-4]\b' | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u); do
  cwd=$(readlink /proc/$pid/cwd 2>/dev/null)
  case "$cwd" in
    /tmp/claude-*|*/test/runs/*) found="$cwd";;
  esac
done
if [ -n "$found" ]; then
  owner=$(cat "$found/.driver" 2>/dev/null | tr -dc '0-9')
  if [ -n "$owner" ] && kill -0 "$owner" 2>/dev/null; then
    exit 0   # a test still running owns it
  fi
  printf '{"decision":"block","reason":"A scratch fleet is still up in %s (a MOOSDB on the 9100 ports) and no running test owns it. Shut it down with ivp/missions/m2_alpha_llm/test/fleet.sh down <that dir>, or say in the reply why it stays up."}\n' "$found"
fi
exit 0
