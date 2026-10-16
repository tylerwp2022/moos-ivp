#!/bin/bash
#  Remove logs and generated artifacts from the turn-test rig.
rm -rf  LOG_* MOOSLog_* XLOG_* *.alog *.ylog *.moos++ 2>/dev/null
rm -f   turn_test_headless.moos targ_*.moos expt_*.moos *.moos++ 2>/dev/null
rm -f   .LastOpenedMOOSLogDirectory 2>/dev/null
echo "turn-test: cleaned logs."
