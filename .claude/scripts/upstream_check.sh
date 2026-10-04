#!/bin/bash
# upstream_check.sh [--list]: the fork's changed or new files that lie
# OUTSIDE its own territory, that is, upstream MOOS-IvP files. Prints
# them and exits 1 when there are any; exits 0 when the change stays
# within the fork. Run before the fork's commit (the commit-all skill):
# an upstream edit that is meant needs its local-patches/NNNN record,
# an accidental one is reverted. The territory: the submodules, the
# CMake registration file, pMarineViewer (the chat pane and ring),
# local-patches/, the fork's missions, the Claude files, and the
# top-level files the fork maintains. Log directories and chat test
# runs are never counted.
set -u
REPO=$(cd "$(dirname "$0")/../.." && pwd)
TERRITORY=(
  ivp/src/moos-ivp-
  ivp/src/pRedirectWaypoint
  ivp/src/uXboxJoystick
  ivp/src/uGfxMask
  ivp/src/CMakeLists.txt
  ivp/src/pMarineViewer/
  local-patches/
  ivp/missions/s1_alpha_llm/
  ivp/missions/m2_alpha_llm/
  ivp/missions/s1_alpha_cot_test/
  .claude/
  .github/
  docker/
  CLAUDE.md
  README
  .gitignore
  .gitmodules
  build-check.sh
  editor-modes/moos-apps.el
)
if [ "${1:-}" = "--list" ]; then
  printf '%s\n' "${TERRITORY[@]}"; exit 0
fi
outside=""
while IFS= read -r line; do
  [ -z "$line" ] && continue
  path=${line:3}
  case "$path" in *" -> "*) path=${path##* -> };; esac
  case "$path" in
    ivp/missions/*/MOOSLog_*|ivp/missions/*/LOG_*|ivp/missions/*/XLOG_*|*/test/runs/*) continue;;
  esac
  ok=""
  for t in "${TERRITORY[@]}"; do
    case "$path" in "$t"*) ok=1; break;; esac
  done
  [ -z "$ok" ] && outside="$outside$path"$'\n'
done < <(git -C "$REPO" status --short)
if [ -n "$outside" ]; then
  echo "changed outside the fork's territory (upstream files):"
  printf '%s' "$outside" | sed 's/^/  /'
  echo "revert them, or keep them with a local-patches/NNNN record"
  exit 1
fi
echo "every change is within the fork's territory"
exit 0
