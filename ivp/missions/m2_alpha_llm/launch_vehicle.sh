#!/bin/bash
#------------------------------------------------------------
#   Script: launch_vehicle.sh
#  Mission: m2_alpha_llm
#  Purpose: Fill meta_vehicle.moos and meta_vehicle.bhv for one
#           simulated vehicle and launch its community. Normally run
#           by launch.sh, which picks the ports and positions.
#------------------------------------------------------------
vecho() { if [ "$VERBOSE" != "" ]; then echo "$ME: $1"; fi }
on_exit() { echo; echo "$ME: Halting all apps"; kill -- -$$; }
trap on_exit SIGINT
trap on_exit SIGTERM

#------------------------------------------------------------
#  Part 1: Global variable defaults
#------------------------------------------------------------
ME=`basename "$0"`
TIME_WARP=1
VERBOSE=""
JUST_MAKE=""
AUTO_LAUNCHED=""

IP_ADDR="localhost"
MOOS_PORT="9001"
PSHARE_PORT="9201"
SHORE_IP="localhost"
SHORE_PSHARE="9200"

VNAME="abe"
COLOR="yellow"
START_POS="x=0,y=-20,heading=180"
RETURN_POS="0,-20"

#------------------------------------------------------------
#  Part 2: Command-line arguments
#------------------------------------------------------------
for ARGI; do
    if [ "${ARGI}" = "--help" -o "${ARGI}" = "-h" ]; then
	echo "$ME [OPTIONS] [time_warp]                                    "
	echo "  --vname=<abe>          Vehicle and community name           "
	echo "  --color=<yellow>       Vehicle color in the viewer           "
	echo "  --start_pos=<x=0,y=-20,heading=180>   Sim start pose         "
	echo "  --return_pos=<0,-20>   Where return and station_keep default "
	echo "  --mport=<9001>         This community's MOOSDB port          "
	echo "  --pshare=<9201>        This community's pShare port          "
	echo "  --shore=<localhost>    Shoreside IP address                  "
	echo "  --shore_pshare=<9200>  Shoreside pShare port                 "
	echo "  --ip=<localhost>       This vehicle's IP, for pHostInfo      "
	echo "  --auto, -a             Launched by a script: no uMAC         "
	echo "  --just_make, -j        Only create the targ files            "
	echo "  --verbose, -v          Verbose launch                        "
	exit 0
    elif [ "${ARGI//[^0-9]/}" = "$ARGI" -a "$TIME_WARP" = 1 ]; then
	TIME_WARP=$ARGI
    elif [ "${ARGI}" = "--verbose" -o "${ARGI}" = "-v" ]; then
	VERBOSE="yes"
    elif [ "${ARGI}" = "--just_make" -o "${ARGI}" = "-j" ]; then
	JUST_MAKE="yes"
    elif [ "${ARGI}" = "--auto" -o "${ARGI}" = "-a" ]; then
	AUTO_LAUNCHED="yes"
    elif [ "${ARGI:0:8}" = "--vname=" ]; then
	VNAME="${ARGI#--vname=*}"
    elif [ "${ARGI:0:8}" = "--color=" ]; then
	COLOR="${ARGI#--color=*}"
    elif [ "${ARGI:0:12}" = "--start_pos=" ]; then
	START_POS="${ARGI#--start_pos=*}"
    elif [ "${ARGI:0:13}" = "--return_pos=" ]; then
	RETURN_POS="${ARGI#--return_pos=*}"
    elif [ "${ARGI:0:8}" = "--mport=" ]; then
	MOOS_PORT="${ARGI#--mport=*}"
    elif [ "${ARGI:0:9}" = "--pshare=" ]; then
	PSHARE_PORT="${ARGI#--pshare=*}"
    elif [ "${ARGI:0:8}" = "--shore=" ]; then
	SHORE_IP="${ARGI#--shore=*}"
    elif [ "${ARGI:0:15}" = "--shore_pshare=" ]; then
	SHORE_PSHARE="${ARGI#--shore_pshare=*}"
    elif [ "${ARGI:0:5}" = "--ip=" ]; then
	IP_ADDR="${ARGI#--ip=*}"
    else
	echo "$ME: Bad arg: $ARGI. Exit code 1."
	exit 1
    fi
done

#------------------------------------------------------------
#  Part 3: Create the .moos and .bhv files
#------------------------------------------------------------
NSFLAGS="--strict --force"
nsplug meta_vehicle.moos targ_$VNAME.moos $NSFLAGS WARP=$TIME_WARP \
       IP_ADDR=$IP_ADDR            MOOS_PORT=$MOOS_PORT        \
       PSHARE_PORT=$PSHARE_PORT    SHORE_IP=$SHORE_IP          \
       SHORE_PSHARE=$SHORE_PSHARE  VNAME=$VNAME                \
       COLOR=$COLOR                START_POS=$START_POS

nsplug meta_vehicle.bhv targ_$VNAME.bhv $NSFLAGS \
       VNAME=$VNAME                RETURN_POS=$RETURN_POS

if [ "${JUST_MAKE}" = "yes" ]; then
    vecho "Targ files made for $VNAME; nothing launched."
    exit 0
fi

#------------------------------------------------------------
#  Part 4: Launch, then uMAC unless a script launched us
#------------------------------------------------------------
echo "$ME: Launching $VNAME (MOOSDB $MOOS_PORT, pShare $PSHARE_PORT, warp $TIME_WARP)"
pAntler targ_$VNAME.moos >& /dev/null &

if [ "${AUTO_LAUNCHED}" = "yes" ]; then
    exit 0
fi

uMAC targ_$VNAME.moos
trap "" SIGINT
echo; echo "$ME: Halting all apps"
kill -- -$$
