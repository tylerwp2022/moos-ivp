#!/bin/bash -e
#----------------------------------------------------------
#  Script: launch.sh
#  Turn-in-place characterization rig.
#
#    ./launch.sh [warp]           GUI: watch the sweep + manual buttons
#    ./launch.sh --nogui [warp]   headless: run sweep, then auto-analyze
#----------------------------------------------------------
TIME_WARP=1
COMMUNITY="turn_test"
GUI="yes"

for ARGI; do
    if [ "${ARGI}" = "--help" -o "${ARGI}" = "-h" ] ; then
	echo "launch.sh [SWITCHES] [time_warp]                         "
	echo "  --nogui    Headless: run the full sweep, kill, analyze.  "
	echo "  --help, -h Show this help message                        "
	exit 0;
    elif [ "${ARGI}" = "--nogui" ] ; then
	GUI="no"
    elif [ "${ARGI//[^0-9]/}" = "$ARGI" -a "$TIME_WARP" = 1 ]; then
        TIME_WARP=$ARGI
    else
        echo "launch.sh Bad arg:" $ARGI " Exiting with code: 1"
        exit 1
    fi
done

# Clear any stragglers from a previous turn-test run that could still be
# holding port 9000 (targeted so we don't disturb other MOOS missions).
pkill -9 -f "${COMMUNITY}.moos" 2>/dev/null || true
pkill -9 -f "targ_${COMMUNITY}" 2>/dev/null || true
sleep 1

if [ "${GUI}" = "yes" ]; then
    echo "Launching $COMMUNITY (GUI) with WARP: $TIME_WARP"
    pAntler $COMMUNITY.moos --MOOSTimeWarp=$TIME_WARP >& /dev/null &
    uMAC -t $COMMUNITY.moos
    kill -- -$$
else
    # Headless: strip pMarineViewer, run the sweep, kill, analyze.
    HEADLESS="targ_${COMMUNITY}_headless.moos"
    awk '
      /Run = pMarineViewer/ { next }
      /^ProcessConfig = pMarineViewer/ { skip=1 }
      skip==1 && /^}/ { skip=0; next }
      skip==1 { next }
      { print }
    ' $COMMUNITY.moos > $HEADLESS

    # Sweep ends near 720 sim-sec; add margin, scale by warp.
    SLEEP=$(( (780 / TIME_WARP) + 6 ))
    echo "Launching $COMMUNITY (headless) WARP:$TIME_WARP  (~${SLEEP}s real)"
    pAntler $HEADLESS --MOOSTimeWarp=$TIME_WARP >& /tmp/${COMMUNITY}_antler.log &
    sleep $SLEEP
    echo "Sweep done; tearing down."
    killmoos >& /dev/null || true
    sleep 2
    echo "-----------------------------------------------------"
    python3 analyze.py || true
fi
