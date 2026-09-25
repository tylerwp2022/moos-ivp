#!/bin/bash -e
#------------------------------------------------------------
#   Script: launch.sh
#  Mission: m2_alpha_llm
#   Author: Tyler Errico, after M. Benjamin's m2_berta
#  Purpose: A small fleet for pLLMAgent. N simulated vehicles, each
#           its own MOOS community running the s1_alpha_llm helm and
#           its own pBehaviorTree, and a shoreside community with
#           pMarineViewer's chat pane and pLLMAgent. See README.
#------------------------------------------------------------
#  Part 1: Convenience functions, SIGINT/SIGTERM handling
#------------------------------------------------------------
vecho() { if [ "$VERBOSE" != "" ]; then echo "$ME: $1"; fi }
on_exit() { echo; echo "$ME: Halting all apps"; kill -- -$$; }
trap on_exit SIGINT
trap on_exit SIGTERM

#------------------------------------------------------------
#  Part 2: Global variable defaults
#------------------------------------------------------------
ME=`basename "$0"`
TIME_WARP=1
VERBOSE=""
JUST_MAKE=""
NOGUI=""
VAMT=2
SHORE_MPORT=9000
SHORE_PSHARE=9200

# One entry per vehicle the fleet can hold; --amt picks the first N.
# Vehicle k gets MOOSDB port SHORE_MPORT+k and pShare SHORE_PSHARE+k.
VNAMES=(abe ben cal deb)
VCOLORS=(yellow red green dodger_blue)
VSTARTS=("x=0,y=-20,heading=180"   "x=30,y=-20,heading=180" \
         "x=-30,y=-20,heading=180" "x=60,y=-20,heading=180")
MAX_VAMT=${#VNAMES[@]}

#------------------------------------------------------------
#  Part 3: Command-line arguments
#------------------------------------------------------------
for ARGI; do
    if [ "${ARGI}" = "--help" -o "${ARGI}" = "-h" ]; then
	echo "$ME [OPTIONS] [time_warp]                                  "
	echo "  --help, -h          Show this help message                "
	echo "  --verbose, -v       Verbose launch                        "
	echo "  --just_make, -j     Only create the targ files            "
	echo "  --nogui, -ng        No pMarineViewer (headless test)      "
	echo "  --amt=N             Vehicles to launch, 1..$MAX_VAMT (default $VAMT)"
	echo "  --shore_mport=P     Shoreside MOOSDB port (default 9000)  "
	echo "  --shore_pshare=P    Shoreside pShare port (default 9200)  "
	echo "                      vehicle k uses P+k for both           "
	exit 0
    elif [ "${ARGI//[^0-9]/}" = "$ARGI" -a "$TIME_WARP" = 1 ]; then
	TIME_WARP=$ARGI
    elif [ "${ARGI}" = "--verbose" -o "${ARGI}" = "-v" ]; then
	VERBOSE=$ARGI
    elif [ "${ARGI}" = "--just_make" -o "${ARGI}" = "-j" ]; then
	JUST_MAKE=$ARGI
    elif [ "${ARGI}" = "--nogui" -o "${ARGI}" = "-ng" ]; then
	NOGUI="--nogui"
    elif [ "${ARGI:0:6}" = "--amt=" ]; then
	VAMT="${ARGI#--amt=*}"
	if [ "$VAMT" -lt 1 -o "$VAMT" -gt "$MAX_VAMT" ]; then
	    echo "$ME: --amt must be 1..$MAX_VAMT. Exit code 2."
	    exit 2
	fi
    elif [ "${ARGI:0:14}" = "--shore_mport=" ]; then
	SHORE_MPORT="${ARGI#--shore_mport=*}"
    elif [ "${ARGI:0:15}" = "--shore_pshare=" ]; then
	SHORE_PSHARE="${ARGI#--shore_pshare=*}"
    else
	echo "$ME: Bad arg: $ARGI. Exit code 1."
	exit 1
    fi
done

if [ -z "$ANTHROPIC_API_KEY" -a "$JUST_MAKE" = "" ]; then
    echo "$ME: ANTHROPIC_API_KEY is not set in this shell. pLLMAgent reads"
    echo "$ME: the key from it; the chat will answer every message with an"
    echo "$ME: error, but the fleet still runs from the viewer and uPokeDB."
fi

#------------------------------------------------------------
#  Part 4: Launch the vehicles
#------------------------------------------------------------
VNAME_LIST=""
for IX in `seq 1 $VAMT`; do
    IXX=$(($IX - 1))
    VNAME=${VNAMES[$IXX]}
    START=${VSTARTS[$IXX]}
    RETURN_POS=`echo $START | sed -E 's/^x=([^,]*),y=([^,]*).*/\1,\2/'`
    if [ "$VNAME_LIST" != "" ]; then
	VNAME_LIST+=":"
    fi
    VNAME_LIST+=$VNAME

    VARGS=" --vname=$VNAME --color=${VCOLORS[$IXX]} --start_pos=$START "
    VARGS+=" --return_pos=$RETURN_POS "
    VARGS+=" --mport=$(($SHORE_MPORT + $IX)) --pshare=$(($SHORE_PSHARE + $IX)) "
    VARGS+=" --shore_pshare=$SHORE_PSHARE --auto $TIME_WARP $JUST_MAKE $VERBOSE "
    vecho "Launching vehicle: $VARGS"
    ./launch_vehicle.sh $VARGS
done

#------------------------------------------------------------
#  Part 5: Launch the shoreside
#------------------------------------------------------------
SARGS=" --auto --mport=$SHORE_MPORT --pshare=$SHORE_PSHARE --vnames=$VNAME_LIST "
SARGS+=" $NOGUI $TIME_WARP $JUST_MAKE $VERBOSE "
vecho "Launching shoreside: $SARGS"
./launch_shoreside.sh $SARGS

if [ "${JUST_MAKE}" != "" ]; then
    echo "$ME: Targ files made; exiting without launch."
    exit 0
fi

#------------------------------------------------------------
#  Part 6: uMAC until the mission is quit, then halt everything
#------------------------------------------------------------
uMAC targ_shoreside.moos
trap "" SIGINT
echo; echo "$ME: Halting all apps"
kill -- -$$
