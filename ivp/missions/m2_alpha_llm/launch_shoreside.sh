#!/bin/bash
#------------------------------------------------------------
#   Script: launch_shoreside.sh
#  Mission: m2_alpha_llm
#  Purpose: Fill meta_shoreside.moos and launch the shoreside
#           community (pMarineViewer, pLLMAgent, the uField apps).
#           Normally run by launch.sh.
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
NOGUI=""

IP_ADDR="localhost"
MOOS_PORT="9000"
PSHARE_PORT="9200"
VNAMES="abe:ben"

#------------------------------------------------------------
#  Part 2: Command-line arguments
#------------------------------------------------------------
for ARGI; do
    if [ "${ARGI}" = "--help" -o "${ARGI}" = "-h" ]; then
	echo "$ME [OPTIONS] [time_warp]                                    "
	echo "  --mport=<9000>       Shoreside MOOSDB port                  "
	echo "  --pshare=<9200>      Shoreside pShare port                  "
	echo "  --ip=<localhost>     Shoreside IP, for pHostInfo            "
	echo "  --vnames=<abe:ben>   The vehicles, for the roster           "
	echo "  --nogui, -ng         No pMarineViewer (headless test)       "
	echo "  --auto, -a           Launched by a script: no uMAC          "
	echo "  --just_make, -j      Only create the targ file              "
	echo "  --verbose, -v        Verbose launch                         "
	exit 0
    elif [ "${ARGI//[^0-9]/}" = "$ARGI" -a "$TIME_WARP" = 1 ]; then
	TIME_WARP=$ARGI
    elif [ "${ARGI}" = "--verbose" -o "${ARGI}" = "-v" ]; then
	VERBOSE="yes"
    elif [ "${ARGI}" = "--just_make" -o "${ARGI}" = "-j" ]; then
	JUST_MAKE="yes"
    elif [ "${ARGI}" = "--auto" -o "${ARGI}" = "-a" ]; then
	AUTO_LAUNCHED="yes"
    elif [ "${ARGI}" = "--nogui" -o "${ARGI}" = "-ng" ]; then
	NOGUI="NOGUI=yes"
    elif [ "${ARGI:0:8}" = "--mport=" ]; then
	MOOS_PORT="${ARGI#--mport=*}"
    elif [ "${ARGI:0:9}" = "--pshare=" ]; then
	PSHARE_PORT="${ARGI#--pshare=*}"
    elif [ "${ARGI:0:5}" = "--ip=" ]; then
	IP_ADDR="${ARGI#--ip=*}"
    elif [ "${ARGI:0:9}" = "--vnames=" ]; then
	VNAMES="${ARGI#--vnames=*}"
    else
	echo "$ME: Bad arg: $ARGI. Exit code 1."
	exit 1
    fi
done

# abe:ben for the launch scripts, abe,ben for pLLMAgent's vnames line
VNAMES_CSV=${VNAMES//:/,}

#------------------------------------------------------------
#  Part 3: Create the .moos file
#------------------------------------------------------------
nsplug meta_shoreside.moos targ_shoreside.moos --strict --force \
       WARP=$TIME_WARP        IP_ADDR=$IP_ADDR          \
       MOOS_PORT=$MOOS_PORT   PSHARE_PORT=$PSHARE_PORT  \
       VNAMES=$VNAMES         VNAMES_CSV=$VNAMES_CSV    \
       $NOGUI

if [ ! -e targ_shoreside.moos ]; then
    echo "$ME: no targ_shoreside.moos was made. Exit code 3."
    exit 3
fi

if [ "${JUST_MAKE}" = "yes" ]; then
    vecho "Shoreside targ file made; nothing launched."
    exit 0
fi

#------------------------------------------------------------
#  Part 4: Launch, then uMAC unless a script launched us
#------------------------------------------------------------
echo "$ME: Launching shoreside (MOOSDB $MOOS_PORT, pShare $PSHARE_PORT, warp $TIME_WARP)"
pAntler targ_shoreside.moos >& /dev/null &

if [ "${AUTO_LAUNCHED}" = "yes" ]; then
    exit 0
fi

uMAC targ_shoreside.moos
trap "" SIGINT
echo; echo "$ME: Halting all apps"
kill -- -$$
