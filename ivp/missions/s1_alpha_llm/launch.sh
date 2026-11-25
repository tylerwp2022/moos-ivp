#!/bin/bash -e
#----------------------------------------------------------
#  Script: launch.sh
#  Author: Michael Benjamin
#  LastEd: May 20th 2019
#  Modified by Timeo Williams on 2026-11-25.
#----------------------------------------------------------

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
mission=alpha.moos
chat_viewer=pmarineviewer
gui=yes
time_warp=

for arg in "$@"; do
    case "$arg" in
        -h|--help)
            cat <<'HELP'
Usage: launch.sh [--chat-viewer=pmarineviewer|umacview] [--nogui] [time_warp]
  pmarineviewer  Open chat in pMarineViewer (default).
  umacview       Open chat in uMACView and keep pMarineViewer for the map.
  --nogui        Run the simulator with no viewer windows.
HELP
            exit 0
            ;;
        --chat-viewer=pmarineviewer|--chat-viewer=umacview) chat_viewer=${arg#*=} ;;
        --nogui) gui=no ;;
        *)
            if [[ -z $time_warp && $arg =~ ^[1-9][0-9]*$ ]]; then
                time_warp=$arg
            else
                printf 'launch.sh: unrecognized argument %s\n' "$arg" >&2
                exit 1
            fi
            ;;
    esac
done

if [[ -z ${OPENAI_API_KEY:-} ]]; then
    echo 'launch.sh: set OPENAI_API_KEY in this shell before starting Alpha.' >&2
    exit 1
fi

if [[ $gui == yes && $OSTYPE == linux* ]]; then
    if [[ -z ${DISPLAY:-} ]] || { command -v xset >/dev/null && ! xset q >/dev/null 2>&1; }; then
        echo 'launch.sh: the Linux display is unavailable. Start WSLg or another X display before opening the viewers.' >&2
        exit 1
    fi
fi

antler_args=("$mission")
viewer_args=()
if [[ $gui == no || $chat_viewer == umacview ]]; then
    # Antler filters the apps in the source mission by name. Start the
    # map viewer separately when it needs the startup chat override.
    processes=$(awk -v gui="$gui" '
        /^[[:space:]]*Run[[:space:]]*=/ {
            sub(/^[[:space:]]*Run[[:space:]]*=[[:space:]]*/, "")
            split($0, entry, /[[:space:]@]+/)
            if (entry[1] != "pMarineViewer" && (gui != "no" || entry[1] != "uButtonPanel"))
                printf "%s ", entry[1]
        }' "$mission")
    antler_args+=("$processes")
fi
if [[ -n $time_warp ]]; then
    antler_args+=("--MOOSTimeWarp=$time_warp")
    viewer_args+=("--moos_time_warp=$time_warp")
fi

pids=()
cleanup() {
    local pid
    for pid in "${pids[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "Launching Alpha with chat in $chat_viewer (GUI $gui)."
pAntler "${antler_args[@]}" >/dev/null 2>&1 &
antler_pid=$!
pids+=("$antler_pid")
if [[ $gui == yes && $chat_viewer == umacview ]]; then
    pMarineViewer "$mission" --no-chat "${viewer_args[@]}" &
    pids+=("$!")
    uMACView "$mission" --alias=uMACView "${viewer_args[@]}" &
    pids+=("$!")
fi

if [[ -t 0 ]]; then
    uMAC -t "$mission" "${viewer_args[@]}"
else
    wait "$antler_pid"
fi
