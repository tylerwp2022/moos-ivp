#!/bin/bash
#--------------------------------------------------------------
#   Script: pr_startup.sh
#  Purpose: Start the current build's app and the pull request's
#           app on the same scratch copy of a mission file, one
#           after the other, on one MOOSDB on port 9100, with no
#           API key in the environment (nothing can be sent), and
#           say for each whether it stayed up or how it died.
#
#    Usage: pr_startup.sh <app> <mission.moos> <pr-bin> <run-dir> [name=sed-script ...]
#
#      <app>           the app under review (pLLMAgent)
#      <mission.moos>  a plain single-community mission file that
#                      holds the app's block (s1_alpha_llm/alpha.moos,
#                      or an already expanded targ_*.moos)
#      <pr-bin>        the folder with the pull request's binary
#                      (<overlay>/bin from pr_build.sh)
#      <run-dir>       a scratch folder; the mission's folder is
#                      copied there without its logs
#      name=script     one variant per argument: the mission file
#                      with `sed -E script` applied, to try each new
#                      line the pull request reads, the ones it is
#                      meant to refuse included. The file as it is
#                      always runs first, as variant "asis".
#
#   An app still up after 6 s is reported "up". One that left early
#   is reported with its exit code, its last lines and, when gdb is
#   there and it died on a signal, a backtrace. The MOOSDB is shut
#   down on the way out: nothing is left on 9100 for the Stop hook.
#--------------------------------------------------------------
set -u
if [ $# -lt 4 ]; then
  sed -n '3,28p' "$0"; exit 2
fi
APP="$1"; MOOS="$(cd "$(dirname "$2")" && pwd -P)/$(basename "$2")"; PRBIN="$(cd "$3" && pwd -P)"; RUN="$4"; shift 4

HERE="$(cd "$(dirname "$0")" && pwd -P)"
R="$(cd "$HERE/../../.." && pwd -P)"
[ -f "$MOOS" ]        || { echo "no mission file: $MOOS"; exit 2; }
[ -x "$PRBIN/$APP" ]  || { echo "no $APP in $PRBIN"; exit 2; }
[ -x "$R/bin/$APP" ]  || { echo "no $APP in $R/bin"; exit 2; }
case "$RUN" in
  "$R"/*) echo "the run folder must be outside the repository: $RUN"; exit 2;;
esac
if ss -ltn 2>/dev/null | grep -qE ':9100\b'; then
  echo "port 9100 is in use: another scratch fleet is up; shut it down first"; exit 2
fi

rm -rf "$RUN"; mkdir -p "$RUN"
MDIR="$(dirname "$MOOS")"
for e in "$MDIR"/*; do
  case "$(basename "$e")" in
    MOOSLog*|LOG*|XLOG*|*.alog|.LastOpenedMOOSLogDirectory) continue;;
  esac
  cp -r "$e" "$RUN/"
done
cd "$RUN"
BASEFILE="$(basename "$MOOS")"
sed -i -E 's/^(ServerPort *= *)[0-9]+/\19100/; s/^( *app_logging *= *)true/\1false/' "$BASEFILE"

cp "$BASEFILE" v_asis.moos
NAMES="asis"
for spec in "$@"; do
  name="${spec%%=*}"; script="${spec#*=}"
  sed -E "$script" "$BASEFILE" > "v_$name.moos"
  if cmp -s "$BASEFILE" "v_$name.moos"; then
    echo "variant $name changed nothing: check its sed script"; exit 2
  fi
  NAMES="$NAMES $name"
done

"$R/bin/MOOSDB" "$BASEFILE" > moosdb.log 2>&1 &
DBPID=$!
trap 'kill $DBPID 2>/dev/null; wait $DBPID 2>/dev/null' EXIT
sleep 1.5
kill -0 $DBPID 2>/dev/null || { echo "MOOSDB did not start:"; tail -5 moosdb.log; exit 1; }

# Every key the fork's apps read, out of the environment
CLEAN="env -u ANTHROPIC_API_KEY -u OPENAI_API_KEY"

one() {   # label, bin folder, variant
  local out="out_$1_$3.txt"
  # in a subshell, so the shell's own "Aborted" line for a crashed app stays out of the report
  ( $CLEAN PATH="$2:$R/bin:$PATH" timeout 6 stdbuf -oL -eL "$APP" "v_$3.moos" > "$out" 2>&1; exit $? ) 2>/dev/null
  local rc=$?
  if [ $rc -eq 124 ]; then
    echo "  [$1] up"
    return
  fi
  echo "  [$1] LEFT EARLY, exit code $rc$( [ $rc -gt 128 ] && echo " (signal $((rc-128)))" )"
  tail -4 "$out" | cut -c1-200 | sed 's/^/        | /'
  if [ $rc -gt 128 ] && command -v gdb >/dev/null 2>&1; then
    $CLEAN PATH="$2:$R/bin:$PATH" timeout 60 gdb -q -batch -ex run -ex bt \
        --args "$2/$APP" --alias="$APP" "v_$3.moos" 2>&1 \
      | grep -a -E '^#[0-9]+' | grep -v -E 'pthread_kill|raise|abort|libstdc|start_thread|clone3' \
      | cut -c1-160 | head -6 | sed 's/^/        bt '/
  fi
}

for v in $NAMES; do
  echo "== $v"
  [ "$v" = "asis" ] || diff <(cat "$BASEFILE") "v_$v.moos" | grep -E '^[<>]' | cut -c1-150 | sed 's/^/     /'
  one current "$R/bin" "$v"
  one PR "$PRBIN" "$v"
done
echo "== MOOSDB down; outputs in $RUN/out_*.txt"
