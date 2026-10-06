#!/bin/bash
# precommit.sh: everything the commit-all skill checks before a commit,
# in one run. Exit 1 and the list of failures when anything is off.
#   territory   no change outside the fork's territory (upstream_check.sh)
#   submodules  each fork submodule on main tracking origin/main, not behind
#   build       build-check.sh finds every expected binary
#   selftests   cap, bt, llm, team self-tests: 0 failures
#   chat test   chat_test.md is current with test/chat_tests.txt
#   fleet       no scratch fleet on the 9100 ports
REPO=$(cd "$(dirname "$0")/../.." && pwd)
fails=""
say()  { printf '  %-10s %s\n' "$1" "$2"; }
fail() { fails="$fails$1: $2"$'\n'; say "$1" "FAIL  $2"; }

if out=$("$REPO/.claude/scripts/upstream_check.sh" 2>&1); then say territory "ok"; else fail territory "$(echo "$out" | head -3 | tr '\n' ' ')"; fi

for m in moos-ivp-llm moos-ivp-bt moos-ivp-cap moos-ivp-team moos-ivp-dyn moos-ivp-panel; do
  d="$REPO/ivp/src/$m"
  [ -d "$d/.git" ] || [ -f "$d/.git" ] || { fail submodules "$m is not a git checkout"; continue; }
  br=$(git -C "$d" symbolic-ref --short -q HEAD)
  [ "$br" = "main" ] || { fail submodules "$m is on '${br:-a detached HEAD}', not main"; continue; }
  git -C "$d" fetch -q origin main 2>/dev/null
  behind=$(git -C "$d" rev-list --count HEAD..origin/main 2>/dev/null)
  [ "${behind:-0}" = "0" ] || fail submodules "$m is $behind commits behind origin/main"
done
[ -z "$(echo "$fails" | grep '^submodules')" ] && say submodules "six on main, none behind"

if out=$("$REPO/build-check.sh" 2>&1); then say build "ok"; else fail build "$(echo "$out" | grep -i missing | head -1)"; fi

for t in cap bt llm team; do
  if [ -x "$REPO/bin/${t}_selftest" ]; then
    line=$("$REPO/bin/${t}_selftest" 2>&1 | grep -E 'checks' | tail -1)
    case "$line" in *" 0 failures"*) say "selftest" "$t: $line";; *) fail selftest "$t: ${line:-did not run}";; esac
  else
    fail selftest "$t: bin/${t}_selftest missing"
  fi
done

if out=$(python3 "$REPO/ivp/missions/m2_alpha_llm/test/chat_test_md.py" --check 2>&1); then say "chat test" "chat_test.md current"; else fail "chat test" "$out (run test/chat_test_md.py)"; fi

if ss -ltnu 2>/dev/null | grep -qE ':9(10[0-4]|30[0-4])\b'; then fail fleet "a scratch fleet is up on the 9100 ports (fleet.sh down)"; else say fleet "9100 ports free"; fi

if [ -n "$fails" ]; then echo; echo "NOT READY TO COMMIT:"; printf '%s' "$fails" | sed 's/^/  /'; exit 1; fi
echo "ready to commit"
