#!/bin/bash
# fleet.sh: a scratch copy of an LLM mission on the 9100 ports.
#   fleet.sh up    <mission_dir> <scratch_dir> <boats 1-4> <warp> [--gui] [--key]
#   fleet.sh ready <scratch_dir> [timeout_s=180]   wait for helms, reports, facts, agent idle
#   fleet.sh run   <scratch_dir> <app> ["config line" ...]   an app outside pAntler, on 9100
#   fleet.sh chat  <scratch_dir> "<line>" [y|n|-] [timeout_s=120]   type, wait, answer, print
#   fleet.sh down  <scratch_dir>
#   fleet.sh alog  <scratch_dir>          the newest shoreside alog, or nothing yet
# up copies the mission files and launches each app in its own subshell
# from the scratch dir (pLogger writes there); the API key is dropped
# unless --key. ready polls each condition and names the one that held
# it up on a timeout. run writes <app>_side.moos with the shoreside's
# port, time warp and datum plus the config lines given, and logs the
# console to <app>.out. chat pokes LLM_CHAT_IN, waits for a proposal or
# a reply, answers y or n if asked (- leaves it pending), and prints
# what the agent said. down kills everything whose cwd is the scratch dir.
set -u
BIN=/home/tyler/moos-ivp/bin
NAMES=(abe ben cal deb)
COLORS=(yellow red green dodger_blue)
STARTS=("x=0,y=-20,heading=180" "x=30,y=-20,heading=180" "x=-30,y=-20,heading=180" "x=60,y=-20,heading=180")
RETURNS=("0,-20" "30,-20" "-30,-20" "60,-20")

cmd=${1:-}; shift || true
case "$cmd" in
  up)
    M=$1; S=$2; AMT=${3:-2}; WARP=${4:-10}; shift 4 || true
    GUI=""; KEYENV="env -u ANTHROPIC_API_KEY"
    for a in "$@"; do
      [ "$a" = "--gui" ] && GUI=1
      [ "$a" = "--key" ] && KEYENV="env"
    done
    if ss -ltnu 2>/dev/null | grep -qE ':9(10[0-4]|30[0-4])\b'; then
      echo "tcp 9100-9104 or udp 9300-9304 in use: an earlier fleet is still up; fleet.sh down <its dir> first"; exit 1
    fi
    mkdir -p "$S"
    cp "$M"/meta_*.moos "$M"/plugs.moos "$M"/meta_vehicle.bhv "$M"/launch_vehicle.sh "$M"/launch_shoreside.sh "$S"/ || exit 1
    rm -rf "$S/plans" "$S/prompts" "$S/dyn"; cp -r "$M/plans" "$M/prompts" "$M/dyn" "$S"/
    VN=""
    for ((i=0; i<AMT; i++)); do
      v=${NAMES[$i]}; VN="${VN:+$VN:}$v"
      (cd "$S" && PATH=$BIN:$PATH $KEYENV setsid nohup ./launch_vehicle.sh --vname=$v --color=${COLORS[$i]} \
         --start_pos=${STARTS[$i]} --return_pos=${RETURNS[$i]} --mport=$((9101+i)) --pshare=$((9301+i)) \
         --shore_pshare=9300 --auto $WARP > $v.log 2>&1 &)
    done
    NOGUI="--nogui"; [ -n "$GUI" ] && NOGUI=""
    (cd "$S" && PATH=$BIN:$PATH $KEYENV setsid nohup ./launch_shoreside.sh --auto $NOGUI --mport=9100 --pshare=9300 \
       --vnames=$VN $WARP > shore.log 2>&1 &)
    echo "launched $VN at warp $WARP in $S (shoreside 9100${GUI:+, with the viewer})"
    ;;
  down)
    S=$1
    for sig in TERM KILL; do
      for p in /proc/[0-9]*; do
        pid=${p#/proc/}; [ "$pid" = "$$" ] && continue
        [ "$(readlink $p/cwd 2>/dev/null)" = "$S" ] && kill -$sig $pid 2>/dev/null
      done
      sleep 3
    done
    # a MOOSDB or pShare that outlived the passes above: by port
    for pid in $(ss -ltnup 2>/dev/null | grep -E ':9(10[0-4]|30[0-4])\b' | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u); do
      [ "$(readlink /proc/$pid/cwd 2>/dev/null)" = "$S" ] && kill -9 $pid 2>/dev/null
    done
    sleep 1
    n=0; for p in /proc/[0-9]*; do [ "$(readlink $p/cwd 2>/dev/null)" = "$S" ] && n=$((n+1)); done
    echo "processes left in $S: $n"; ss -ltnu 2>/dev/null | grep -E ':9(10[0-4]|30[0-4])\b' || echo "tcp 9100-9104 and udp 9300-9304 free"
    ;;
  alog)
    ls "$1"/XLOG_SHORESIDE_*/*.alog 2>/dev/null | tail -1
    ;;
  ready)
    S=$1; LIMIT=${2:-180}; SH=$S/targ_shoreside.moos
    WARP=$(grep -m1 "^MOOSTimeWarp" "$SH" 2>/dev/null | tr -dc '0-9.'); WARP=${WARP:-1}
    BOATS=""
    T0=$(date +%s); LEFT=""
    while true; do
      LEFT=""
      BOATS=$(ls "$S"/targ_*.moos 2>/dev/null | xargs -r -n1 basename | sed 's/targ_//; s/.moos//' | grep -v shoreside)
      [ -z "$BOATS" ] && LEFT="the boats' targ files"
      [ -f "$SH" ] || LEFT="the shoreside targ file"
      A=$(ls "$S"/XLOG_SHORESIDE_*/*.alog 2>/dev/null | tail -1)
      [ -z "$A" ] && LEFT="shoreside log"
      for v in $BOATS; do
        if [ -z "$LEFT" ]; then
          timeout 20 $BIN/uQueryDB "$S/targ_$v.moos" --condition="(IVPHELM_STATE = PARK) or (IVPHELM_STATE = DRIVE)" --wait=$((5*WARP)) >/dev/null 2>&1 || LEFT="$v helm"
        fi
        [ -z "$LEFT" ] && { grep -q "NAME=$v" "$A" || LEFT="$v node report on the shoreside"; }
        [ -z "$LEFT" ] && { timeout 20 $BIN/uQueryDB "$SH" --condition="VEHICLE_FACTS_$(echo $v | tr a-z A-Z) != none" --wait=$((5*WARP)) >/dev/null 2>&1 || LEFT="$v facts on the shoreside"; }
      done
      if [ -z "$LEFT" ] && grep -q "pLLMAgent" "$SH"; then
        timeout 20 $BIN/uQueryDB "$SH" --condition="LLM_STATUS = idle" --wait=$((5*WARP)) >/dev/null 2>&1 || LEFT="agent idle"
      fi
      NOW=$(( $(date +%s) - T0 ))
      if [ -z "$LEFT" ]; then echo "ready after ${NOW}s: $(echo $BOATS | tr '\n' ' ') helms, reports, facts, agent idle"; exit 0; fi
      if [ $NOW -ge $LIMIT ]; then echo "not ready after ${NOW}s, still waiting for: $LEFT"; exit 1; fi
      sleep 2
    done
    ;;
  run)
    S=$1; APP=$2; shift 2 || true; SH=$S/targ_shoreside.moos
    [ -f "$SH" ] || { echo "no $SH yet: fleet.sh up first"; exit 1; }
    for p in /proc/[0-9]*; do
      [ "$(readlink $p/cwd 2>/dev/null)" = "$S" ] && [ "$(cat $p/comm 2>/dev/null)" = "$APP" ] && \
        echo "note: a $APP already runs in $S (pid ${p#/proc/}); this will be a second one"
    done
    SIDE="$S/${APP}_side.moos"
    { echo "ServerHost = localhost"; echo "ServerPort = 9100"; echo "Community  = shoreside"
      grep -m1 "^MOOSTimeWarp" "$SH"; grep -m1 "^LatOrigin" "$SH"; grep -m1 "^LongOrigin" "$SH"
      echo; echo "ProcessConfig = $APP"; echo "{"; echo "  AppTick   = 4"; echo "  CommsTick = 4"
      for line in "$@"; do echo "  $line"; done; echo "}"; } > "$SIDE"
    (cd "$S" && PATH=$BIN:$PATH setsid nohup "$APP" "$(basename $SIDE)" > "$APP.out" 2>&1 &)
    sleep 1
    echo "$APP launched on 9100 from $S: config $SIDE, console $S/$APP.out"
    ;;
  chat)
    S=$1; LINE=$2; ANSWER=${3:--}; LIMIT=${4:-120}; SH=$S/targ_shoreside.moos
    WARP=$(grep -m1 "^MOOSTimeWarp" "$SH" 2>/dev/null | tr -dc '0-9.'); WARP=${WARP:-1}
    A=$(ls "$S"/XLOG_SHORESIDE_*/*.alog 2>/dev/null | tail -1)
    [ -z "$A" ] && { echo "no shoreside log yet"; exit 1; }
    show() { grep " LLM_CHAT_OUT " "$A" | grep -v " APPCAST " | tail -n +$(( $1 + 1 )) | \
             awk '{ $1=""; $2=""; $3=""; sub(/^ +/, ""); print }' | sed 's/!@#/\n   /g' | cut -c1-700; }
    N0=$(grep " LLM_CHAT_OUT " "$A" | grep -v " APPCAST " | wc -l)
    $BIN/uPokeDB "$SH" "LLM_CHAT_IN:=$LINE" >/dev/null 2>&1
    # The agent goes thinking, then idle, awaiting_confirm or error=<code>;
    # a reply that needs no model call (a note, a missing key) skips thinking
    timeout 15 $BIN/uQueryDB "$SH" --condition="LLM_STATUS = thinking" --wait=$((3*WARP)) >/dev/null 2>&1
    if ! timeout $((LIMIT+5)) $BIN/uQueryDB "$SH" --condition="LLM_STATUS != thinking" --wait=$((LIMIT*WARP)) >/dev/null 2>&1; then
      echo "no answer within ${LIMIT}s"; show $N0; exit 1
    fi
    sleep 1
    STATUS="other"
    for st in awaiting_confirm idle thinking; do
      timeout 10 $BIN/uQueryDB "$SH" --condition="LLM_STATUS = $st" --wait=1 >/dev/null 2>&1 && { STATUS=$st; break; }
    done
    echo "agent: $STATUS"; show $N0
    if [ "$STATUS" = "awaiting_confirm" ] && [ "$ANSWER" != "-" ]; then
      N1=$(grep " LLM_CHAT_OUT " "$A" | grep -v " APPCAST " | wc -l)
      $BIN/uPokeDB "$SH" "LLM_CHAT_IN:=$ANSWER" >/dev/null 2>&1
      timeout 15 $BIN/uQueryDB "$SH" --condition="LLM_STATUS = thinking" --wait=$((3*WARP)) >/dev/null 2>&1
      timeout $((LIMIT+5)) $BIN/uQueryDB "$SH" --condition="LLM_STATUS != thinking" --wait=$((LIMIT*WARP)) >/dev/null 2>&1
      sleep 1
      echo "answered $ANSWER:"; show $N1
    fi
    ;;
  *)
    sed -n 2,16p "$0"; exit 2
    ;;
esac
