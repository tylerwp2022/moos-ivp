#!/bin/bash
# fleet.sh: a scratch copy of an LLM mission on the 9100 ports.
#   fleet.sh up   <mission_dir> <scratch_dir> <boats 1-4> <warp> [--gui] [--key]
#   fleet.sh down <scratch_dir>
#   fleet.sh alog <scratch_dir>          the newest shoreside alog, or nothing yet
# up copies the mission files and launches each app in its own subshell
# from the scratch dir (pLogger writes there); the API key is dropped
# unless --key. down kills everything whose cwd is the scratch dir.
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
  *)
    sed -n 2,8p "$0"; exit 2
    ;;
esac
