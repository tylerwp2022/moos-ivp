#!/bin/bash
# precommit.sh: everything the commit-all skill checks before a commit,
# in one run. Exit 1 and the list of failures when anything is off.
#   territory   no change outside the fork's territory (upstream_check.sh)
#   submodules  each fork submodule on main tracking origin/main, not behind
#   build       the incremental build in build/ivp relinks anything stale (an
#               app not rebuilt after a lib_* change would pass the next
#               check and run old code: the empty panel of 2026-10-06),
#               then build-check.sh finds every expected binary
#   plays       pBehaviorTree --check-plays accepts every saved plan in the
#               missions' buttons files (parameters at their defaults)
#   selftests   cap, field, bt, llm, squad self-tests: 0 failures
#   chat test   chat_test.md is current with test/chat_tests.txt
#   fleet       no scratch fleet on the 9100 ports
REPO=$(cd "$(dirname "$0")/../.." && pwd)
fails=""
say()  { printf '  %-10s %s\n' "$1" "$2"; }
fail() { fails="$fails$1: $2"$'\n'; say "$1" "FAIL  $2"; }

if out=$("$REPO/.claude/scripts/upstream_check.sh" 2>&1); then say territory "ok"; else fail territory "$(echo "$out" | head -3 | tr '\n' ' ')"; fi

for m in moos-ivp-llm moos-ivp-bt moos-ivp-cap moos-ivp-squad moos-ivp-dyn moos-ivp-panel; do
  d="$REPO/ivp/src/$m"
  [ -d "$d/.git" ] || [ -f "$d/.git" ] || { fail submodules "$m is not a git checkout"; continue; }
  br=$(git -C "$d" symbolic-ref --short -q HEAD)
  [ "$br" = "main" ] || { fail submodules "$m is on '${br:-a detached HEAD}', not main"; continue; }
  git -C "$d" fetch -q origin main 2>/dev/null
  behind=$(git -C "$d" rev-list --count HEAD..origin/main 2>/dev/null)
  [ "${behind:-0}" = "0" ] || fail submodules "$m is $behind commits behind origin/main"
done
[ -z "$(echo "$fails" | grep '^submodules')" ] && say submodules "six on main, none behind"

if [ -d "$REPO/build/ivp" ]; then
  if out=$(make -C "$REPO/build/ivp" -j8 2>&1); then
    n=$(echo "$out" | grep -c 'Linking CXX')
    say build "incremental make ok, $n target$([ "$n" = 1 ] || echo s) relinked"
  else
    fail build "make: $(echo "$out" | grep -iE 'error' | head -1)"
  fi
else
  fail build "build/ivp is missing: run ./build-ivp.sh first"
fi
if out=$("$REPO/build-check.sh" 2>&1); then say build "every expected binary present"; else fail build "$(echo "$out" | grep -i missing | head -1)"; fi

# Every saved plan in each mission's buttons file, with its parameters at
# their defaults, through the executor's own checker
for bf in ivp/missions/m2_alpha_llm/buttons.txt ivp/missions/s1_alpha_llm/buttons.txt; do
  [ -f "$REPO/$bf" ] || continue
  if out=$("$REPO/bin/pBehaviorTree" --check-plays="$REPO/$bf" --vnames=abe,ben,cal,deb 2>&1); then
    say plays "$(basename "$(dirname "$bf")"): $(echo "$out" | tail -1)"
  else
    fail plays "$bf: $(echo "$out" | grep -i rejected | head -1)"
  fi
done

for t in cap field bt llm squad; do
  if [ -x "$REPO/bin/${t}_selftest" ]; then
    line=$("$REPO/bin/${t}_selftest" 2>&1 | grep -E 'checks' | tail -1)
    case "$line" in *" 0 failures"*|*" 0 failed"*) say "selftest" "$t: $line";; *) fail selftest "$t: ${line:-did not run}";; esac
  else
    fail selftest "$t: bin/${t}_selftest missing"
  fi
done

if out=$(python3 "$REPO/ivp/missions/m2_alpha_llm/test/chat_test_md.py" --check 2>&1); then say "chat test" "chat_test.md current"; else fail "chat test" "$out (run test/chat_test_md.py)"; fi

if ss -ltnu 2>/dev/null | grep -qE ':9(10[0-4]|30[0-4])\b'; then fail fleet "a scratch fleet is up on the 9100 ports (fleet.sh down)"; else say fleet "9100 ports free"; fi

if [ -n "$fails" ]; then echo; echo "NOT READY TO COMMIT:"; printf '%s' "$fails" | sed 's/^/  /'; exit 1; fi
echo "ready to commit"
