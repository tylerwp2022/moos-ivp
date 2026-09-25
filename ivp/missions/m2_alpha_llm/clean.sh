#!/bin/bash
#--------------------------------------------------------------
#   Script: clean.sh
#  Mission: m2_alpha_llm
#  Purpose: Remove logs and generated targ files.
#--------------------------------------------------------------
VERBOSE=""
for ARGI; do
    if [ "${ARGI}" = "--help" -o "${ARGI}" = "-h" ] ; then
	echo "clean.sh [SWITCHES]        "
	echo "  --verbose, -v            "
	echo "  --help, -h               "
	exit 0
    elif [ "${ARGI}" = "--verbose" -o "${ARGI}" = "-v" ] ; then
	VERBOSE="-v"
    else
	echo "clean.sh: Bad arg: $ARGI. Exit code 1."
	exit 1
    fi
done

if [ "${VERBOSE}" = "-v" ]; then
    echo "Cleaning: $PWD"
fi
rm -rf  $VERBOSE   MOOSLog_*  XLOG_* LOG_*
rm -f   $VERBOSE   *~  *.moos++
rm -f   $VERBOSE   targ_*
rm -f   $VERBOSE   .LastOpenedMOOSLogDirectory
