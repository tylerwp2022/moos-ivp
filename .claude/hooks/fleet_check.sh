#!/bin/bash
# Claude Code Stop hook: a scratch fleet left running on the 9100 ports
# (a MOOSDB whose working directory is one of Claude's scratch folders,
# the session scratchpad under /tmp/claude-* or a chat test run under
# test/runs/) blocks the turn from ending, with a reason that names the
# folder, until it is shut down or the reply says why it stays up. The
# user's own missions on 9000, or anything not started from a scratch
# folder, never trigger it. Silent and exit 0 otherwise. Reads the
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
  printf '{"decision":"block","reason":"A scratch fleet is still up in %s (a MOOSDB on the 9100 ports). Shut it down with ivp/missions/m2_alpha_llm/test/fleet.sh down <that dir>, or say in the reply why it stays up."}\n' "$found"
fi
exit 0
