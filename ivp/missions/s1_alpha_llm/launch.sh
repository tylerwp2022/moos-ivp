#!/bin/bash -e
#----------------------------------------------------------
#  Script: launch.sh
#  Author: Michael Benjamin
#  LastEd: May 20th 2019
#  Modified by Timeo Williams on 2026-11-25.
#----------------------------------------------------------
#  Environment:
#    OPENAI_API_KEY   OpenAI project key read by pLLMAgent.
#    PATH             Include the built MOOS-IvP bin directory.
#----------------------------------------------------------
#  Part 1: Declare global variable defaults
#----------------------------------------------------------

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
COMMUNITY="alpha"
MISSION="$COMMUNITY.moos"
CHAT_VIEWER="pmarineviewer"
GUI="yes"
TIME_WARP=""  # alpha.moos supplies the default unless an override is passed.

#----------------------------------------------------------
#  Part 2: Check for and handle command-line arguments
#----------------------------------------------------------
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
        --chat-viewer=pmarineviewer|--chat-viewer=umacview) CHAT_VIEWER=${arg#*=} ;;
        --nogui) GUI=no ;;
        *)
            if [[ -z $TIME_WARP && $arg =~ ^[1-9][0-9]*$ ]]; then
                TIME_WARP=$arg
            else
                printf 'launch.sh: unrecognized argument %s\n' "$arg" >&2
                exit 1
            fi
            ;;
    esac
done

#----------------------------------------------------------
#  Part 3: Check the environment and launch the processes
#----------------------------------------------------------
if [[ -z ${OPENAI_API_KEY:-} ]]; then
    echo 'launch.sh: set OPENAI_API_KEY in this shell before starting Alpha.' >&2
    exit 1
fi

if [[ $GUI == yes && $OSTYPE == linux* ]]; then
    if [[ -z ${DISPLAY:-} ]] || { command -v xset >/dev/null && ! xset q >/dev/null 2>&1; }; then
        echo 'launch.sh: the Linux display is unavailable. Start WSLg or another X display before opening the viewers.' >&2
        exit 1
    fi
fi

antler_args=("$MISSION")
viewer_args=()
if [[ $GUI == no || $CHAT_VIEWER == umacview ]]; then
    # Antler filters the apps in the source mission by name. Start the
    # map viewer separately when it needs the startup chat override.
    processes=$(awk -v gui="$GUI" '
        /^[[:space:]]*Run[[:space:]]*=/ {
            sub(/^[[:space:]]*Run[[:space:]]*=[[:space:]]*/, "")
            split($0, entry, /[[:space:]@]+/)
            if (entry[1] != "pMarineViewer" && (gui != "no" || entry[1] != "uButtonPanel"))
                printf "%s ", entry[1]
        }' "$MISSION")
    antler_args+=("$processes")
fi
if [[ -n $TIME_WARP ]]; then
    antler_args+=("--MOOSTimeWarp=$TIME_WARP")
    viewer_args+=("--moos_time_warp=$TIME_WARP")
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

echo "Launching $COMMUNITY MOOS community with chat in $CHAT_VIEWER (GUI $GUI)."
pAntler "${antler_args[@]}" >/dev/null 2>&1 &
antler_pid=$!
pids+=("$antler_pid")
if [[ $GUI == yes && $CHAT_VIEWER == umacview ]]; then
    pMarineViewer "$MISSION" --no-chat "${viewer_args[@]}" &
    pids+=("$!")
    uMACView "$MISSION" --alias=uMACView "${viewer_args[@]}" &
    pids+=("$!")
fi

if [[ -t 0 ]]; then
    uMAC -t "$MISSION" "${viewer_args[@]}"
else
    wait "$antler_pid"
fi
