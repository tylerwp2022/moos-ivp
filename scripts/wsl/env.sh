#!/usr/bin/env bash
# Modified by Timeo Williams on 2026-11-25.
export MOOS_IVP_WSL_ROOT=${MOOS_IVP_WSL_ROOT:-"$HOME/Projects/moos-ivp-wsl"}
export PATH="$MOOS_IVP_WSL_ROOT/moos-ivp/bin:$MOOS_IVP_WSL_ROOT/moos-ivp-mctf/bin:$PATH"
export IVP_BEHAVIOR_DIRS="$MOOS_IVP_WSL_ROOT/moos-ivp/lib:$MOOS_IVP_WSL_ROOT/moos-ivp-mctf/lib"
export LD_LIBRARY_PATH="$MOOS_IVP_WSL_ROOT/moos-ivp/build/MOOS/MOOSGeodesy/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export MOOSIVP_IMAGE_DIR=${MOOSIVP_IMAGE_DIR:-"$MOOS_IVP_WSL_ROOT/moos-ivp/ivp/data"}
