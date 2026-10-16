#!/bin/bash -e
#----------------------------------------------------------
#  launch_demo.sh -- behavior-integrated turn-in-place demo
#    ./launch_demo.sh [time_warp]
#
#  In the GUI: DEPLOY (station-keep) -> TURN180 (BHV_TurnInPlace fires
#  a shuffle 180 via pTurnInPlace under MOOS_MANUAL_OVERRIDE) -> control
#  returns to station-keep automatically. STATION forces station-keep;
#  STOP undeploys.
#----------------------------------------------------------
TIME_WARP=1
COMMUNITY="turn_demo"

for ARGI; do
    if [ "${ARGI}" = "--help" -o "${ARGI}" = "-h" ] ; then
	echo "launch_demo.sh [time_warp]"; exit 0;
    elif [ "${ARGI//[^0-9]/}" = "$ARGI" -a "$TIME_WARP" = 1 ]; then
        TIME_WARP=$ARGI
    else
        echo "launch_demo.sh Bad arg: $ARGI"; exit 1
    fi
done

# Clear stragglers from a prior run (targeted).
pkill -9 -f "${COMMUNITY}.moos" 2>/dev/null || true
sleep 1

echo "Launching $COMMUNITY (GUI) with WARP: $TIME_WARP"
pAntler $COMMUNITY.moos --MOOSTimeWarp=$TIME_WARP >& /dev/null &
uMAC -t $COMMUNITY.moos
kill -- -$$
