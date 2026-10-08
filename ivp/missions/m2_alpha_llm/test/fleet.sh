#!/bin/bash
# fleet.sh: a scratch copy of an LLM mission on the 9100 ports.
#   fleet.sh up    <mission_dir> <scratch_dir> <boats 1-4> <warp> [--gui] [--key]
#   fleet.sh ready <scratch_dir> [timeout_s=180]   wait for helms, reports, facts, agent idle
#   fleet.sh run   <scratch_dir> <app> ["config line" ...]   an app outside pAntler, on 9100
#   fleet.sh chat  <scratch_dir> "<line>" [y|n|-] [timeout_s=120]   type, wait, answer, print
#   fleet.sh plan  <scratch_dir> <plan.xml> <vname|squad> [timeout_s=240]   copy the plan in, poke it, wait for its end
#   fleet.sh squad  <scratch_dir> <name> <a:b[:c]>   create a squad and wait for its slot
#   fleet.sh dump  <scratch_dir> [sections]   the run's record so far (review.py: plans,says,problems,drawings,holds)
#   fleet.sh down  <scratch_dir>
#   fleet.sh alog  <scratch_dir>          the newest shoreside alog, or nothing yet
# up copies the mission files and launches each app in its own subshell
# from the scratch dir (pLogger writes there); the API key is dropped
# unless --key. ready polls each condition and names the one that held
# it up on a timeout. run writes <app>_side.moos with the shoreside's
# port, time warp and datum plus the config lines given, and logs the
# console to <app>.out. chat pokes LLM_CHAT_IN, waits for a proposal or
# a reply, answers y or n if asked (- leaves it pending), and prints
# what the agent said. plan copies the file into <scratch>/plans/ (a path
# already there is used as is), posts BT_TREE_FILE_<OWNER>=plans/<file>
# on the shoreside, waits for running and then for success, failure or
# halted, and prints the outcome with the time it took; exit 0 on success.
# squad posts SQUAD_CMD create and waits for the squad's plan slot to open.
# dump prints review.py's tables for the shoreside alog so far, the plan
# sections by default or the comma list given. down kills everything whose
# cwd is the scratch dir.
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
    [ -f "$M/buttons.txt" ] && cp "$M/buttons.txt" "$S"/   # the button panel's file, pLLMAgent writes to the copy
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
    # Who owns this fleet: the script that called up. The Stop hook
    # (.claude/hooks/fleet_check.sh) lets a fleet whose owner is still
    # running pass, and complains about one whose owner is gone.
    echo $PPID > "$S/.driver"
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
    rm -f "$S/.driver"
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
  plan)
    S=$1; PLAN=$2; OWNER=$(echo "$3" | tr a-z A-Z); LIMIT=${4:-240}; SH=$S/targ_shoreside.moos
    [ -f "$SH" ] || { echo "no $SH yet: fleet.sh up first"; exit 1; }
    WARP=$(grep -m1 "^MOOSTimeWarp" "$SH" 2>/dev/null | tr -dc '0-9.'); WARP=${WARP:-1}
    mkdir -p "$S/plans"
    NAME=$(basename "$PLAN")
    if [ -f "$PLAN" ] && [ "$(readlink -f "$PLAN")" != "$(readlink -f "$S/plans/$NAME")" ]; then cp "$PLAN" "$S/plans/$NAME"; fi
    [ -f "$S/plans/$NAME" ] || { echo "no such plan: $PLAN"; exit 1; }
    # a boat's plan checks as such; anything else is a squad, checked
    # with the fleet's boats as the roster
    BOATS=$(ls "$S"/targ_*.moos 2>/dev/null | xargs -r -n1 basename | sed 's/targ_//; s/.moos//' | grep -v shoreside | tr '\n' ',' | sed 's/,$//')
    CHECK=""
    echo ",$BOATS," | grep -q ",$(echo $OWNER | tr A-Z a-z)," || CHECK="--squad --roster=$BOATS"
    $BIN/pBehaviorTree --check="$S/plans/$NAME" $CHECK >/dev/null 2>&1 || { echo "plan does not check: pBehaviorTree --check=$S/plans/$NAME $CHECK"; exit 1; }
    # The outcome is read from the shoreside log, not polled from the
    # DB: a plan that ends within one tick is running too briefly for a
    # poll to see, and the DB's current value may be an earlier plan's
    A=$(ls "$S"/XLOG_SHORESIDE_*/*.alog 2>/dev/null | tail -1)
    [ -z "$A" ] && { echo "no shoreside log yet"; exit 1; }
    T0=$(date +%s)
    $BIN/uPokeDB "$SH" "BT_TREE_FILE_$OWNER=plans/$NAME" >/dev/null 2>&1
    END=""; RAN=""
    while true; do
      # the poke's own line gives the log time it landed; states after it are this plan's
      LT=$(grep -E "^\S+\s+BT_TREE_FILE_$OWNER\s" "$A" | tail -1 | awk '{print $1}')
      if [ -n "$LT" ]; then
        STATES=$(awk -v lt="$LT" -v v="BT_STATE_$OWNER" '$2==v && $1>=lt {print $4}' "$A" | tr '\n' ' ')
        case " $STATES" in *" running"*) RAN=1;; esac
        for st in success failure halted; do case " $STATES" in *" $st"*) END=$st;; esac; done
        case " $STATES" in *"error="*) END=$(echo "$STATES" | tr ' ' '\n' | grep -m1 error=);; esac
      fi
      [ -n "$END" ] && break
      NOW=$(( $(date +%s) - T0 ))
      if [ $NOW -ge $LIMIT ]; then break; fi
      sleep 1
    done
    DT=$(( $(date +%s) - T0 ))
    V=$(echo $OWNER | tr A-Z a-z)
    if [ -z "$END" ] && [ -z "$RAN" ]; then
      echo "plan $NAME on $V: never ran within ${DT}s (is the owner a boat or an existing squad?)"; exit 1
    fi
    echo "plan $NAME on $V: ${END:-still running} after ${DT}s real ($((DT*${WARP%.*})) warped)"
    [ "$END" = "success" ]
    ;;
  squad)
    S=$1; NAME=$2; MEMBERS=$3; SH=$S/targ_shoreside.moos
    [ -f "$SH" ] || { echo "no $SH yet: fleet.sh up first"; exit 1; }
    WARP=$(grep -m1 "^MOOSTimeWarp" "$SH" 2>/dev/null | tr -dc '0-9.'); WARP=${WARP:-1}
    $BIN/uPokeDB "$SH" "SQUAD_CMD:=action=create,name=$NAME,members=$MEMBERS" >/dev/null 2>&1
    UP=$(echo "$NAME" | tr a-z A-Z)
    if timeout 30 $BIN/uQueryDB "$SH" --condition="BT_STATE_$UP = idle" --wait=$((20*WARP)) >/dev/null 2>&1; then
      echo "squad $NAME ($MEMBERS) created, plan slot open"
    else
      echo "squad $NAME: no plan slot after 20 s (uFldSquad or the squad executor not up?)"; exit 1
    fi
    ;;
  dump)
    S=$1; SECTIONS=${2:-plans,says,problems,drawings,holds}
    A=$(ls "$S"/XLOG_SHORESIDE_*/*.alog 2>/dev/null | tail -1)
    [ -z "$A" ] && { echo "no shoreside log yet"; exit 1; }
    python3 "$(dirname "$0")/review.py" "$A" --only "$SECTIONS"
    # A boat's events never reach the shoreside log: its first-step
    # wait is read from its own alog (load -> running -> first event)
    case ",$SECTIONS," in *,holds,*)
      for V in "$S"/LOG_*_*/*.alog; do
        [ -f "$V" ] || continue
        vn=$(basename "$V" | sed -E 's/^LOG_([A-Za-z0-9]+)_.*/\1/' | tr A-Z a-z)
        awk -v vn="$vn" '($2=="BT_TREE_FILE"||$2=="BT_TREE")&&$1!=last{last=$1; lt=$1; rt=""; et=""} $2=="BT_STATE"&&$4=="running"&&lt!=""&&rt==""{rt=$1} $2=="BT_EVENT"&&rt!=""&&et==""&&$1>=rt{et=$1; printf "%9.1f %8s running +%.2f s, first event +%.2f s (own log)\n", lt, vn, rt-lt, et-rt; lt=""}' "$V"
      done;;
    esac
    ;;
  *)
    sed -n 2,19p "$0"; exit 2
    ;;
esac
