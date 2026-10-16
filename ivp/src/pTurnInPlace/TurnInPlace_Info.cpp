/************************************************************/
/*    NAME: Turn-in-place characterization                  */
/*    ORGN: West Point Robotics Research Center             */
/*    FILE: TurnInPlace_Info.cpp                            */
/*    DATE: 2026                                            */
/************************************************************/

#include <cstdlib>
#include <iostream>
#include "TurnInPlace_Info.h"
#include "ColorParse.h"
#include "ReleaseInfo.h"

using namespace std;

//----------------------------------------------------------------
// Procedure: showSynopsis

void showSynopsis()
{
  blk("SYNOPSIS:                                                       ");
  blk("------------------------------------                            ");
  blk("  pTurnInPlace rotates a rudder-steered surface craft to a      ");
  blk("  commanded compass heading while holding position within a     ");
  blk("  tolerance. It drives DESIRED_RUDDER and DESIRED_THRUST        ");
  blk("  directly (no helm, no PID), so it can command reverse and     ");
  blk("  execute K-turn style maneuvers. Several turning modalities    ");
  blk("  (circle, kturn, shuffle) are provided so the speed-vs-        ");
  blk("  footprint tradeoff can be measured. On each maneuver it posts ");
  blk("  a TURN_RESULT summary (time, footprint, final errors).        ");
  blk("                                                                ");
  blk("  NOTE: reverse rotation requires the legacy uSimMarine (dep)   ");
  blk("  turn model; it does NOT work in uSimMarineV23.                ");
}

//----------------------------------------------------------------
// Procedure: showHelpAndExit

void showHelpAndExit()
{
  blk("                                                                ");
  blu("=============================================================== ");
  blu("Usage: pTurnInPlace file.moos [OPTIONS]                         ");
  blu("=============================================================== ");
  blk("                                                                ");
  showSynopsis();
  blk("                                                                ");
  blk("Options:                                                        ");
  mag("  --alias","=<ProcessName>                                      ");
  blk("      Launch pTurnInPlace with the given process name.          ");
  mag("  --example, -e                                                 ");
  blk("      Display example MOOS configuration block.                 ");
  mag("  --help, -h                                                    ");
  blk("      Display this help message.                                ");
  mag("  --interface, -i                                               ");
  blk("      Display MOOS publications and subscriptions.              ");
  mag("  --version,-v                                                  ");
  blk("      Display release version of pTurnInPlace.                  ");
  blk("                                                                ");
  exit(0);
}

//----------------------------------------------------------------
// Procedure: showExampleConfigAndExit

void showExampleConfigAndExit()
{
  blk("                                                                ");
  blu("=============================================================== ");
  blu("pTurnInPlace Example MOOS Configuration                         ");
  blu("=============================================================== ");
  blk("                                                                ");
  blk("ProcessConfig = pTurnInPlace                                    ");
  blk("{                                                               ");
  blk("  AppTick   = 10                                                ");
  blk("  CommsTick = 10                                                ");
  blk("                                                                ");
  blk("  strategy      = kturn    // circle | kturn | shuffle          ");
  blk("  rudder_max    = 100      // [0,100]                           ");
  blk("  fwd_thrust    = 60       // > 0                               ");
  blk("  rev_thrust    = -60      // < 0                               ");
  blk("  heading_tol   = 5        // deg                               ");
  blk("  settle_time   = 2        // s within tol before done          ");
  blk("  footprint_cap = 6        // m; kturn leg-switch threshold     ");
  blk("  return_frac   = 0.25     // reverse until excursion<=frac*cap ");
  blk("  phase_time    = 3        // s; shuffle leg duration           ");
  blk("  max_run_time  = 120      // s; per-maneuver safety timeout     ");
  blk("  manage_override = true   // seize/release MOOS_MANUAL_OVERRIDE ");
  blk("  override_var  = MOOS_MANUAL_OVERRIDE                           ");
  blk("}                                                               ");
  blk("                                                                ");
  exit(0);
}

//----------------------------------------------------------------
// Procedure: showInterfaceAndExit

void showInterfaceAndExit()
{
  blk("                                                                ");
  blu("=============================================================== ");
  blu("pTurnInPlace INTERFACE                                          ");
  blu("=============================================================== ");
  blk("                                                                ");
  blk("SUBSCRIPTIONS:                                                  ");
  blk("------------------------------------                            ");
  blk("  NAV_X, NAV_Y, NAV_HEADING, NAV_SPEED                          ");
  blk("  TURN_REQUEST = heading=90,strategy=kturn,tol=5,id=t1          ");
  blk("     keys: heading|delta, x, y, strategy, tol, settle,          ");
  blk("           fwd_thrust, rev_thrust, rudder, cap, return_frac,    ");
  blk("           phase_time, id                                       ");
  blk("  TURN_STOP  (any value: abort current maneuver)                ");
  blk("                                                                ");
  blk("PUBLICATIONS:                                                   ");
  blk("------------------------------------                            ");
  blk("  DESIRED_THRUST, DESIRED_RUDDER                                ");
  blk("  TURN_STATE   = RUNNING:FWD | RUNNING:REV | DONE | TIMEOUT     ");
  blk("  TURN_HDG_ERR, TURN_EXCURSION  (live)                          ");
  blk("  TURN_RESULT  = id=..,strategy=..,delta=..,t_elapsed=..,       ");
  blk("                 max_excursion=..,bbox_diag=..,final_pos_err=.. ");
  blk("  TURN_DONE    = <trial id>                                     ");
  blk("  VIEW_POINT   (station marker)                                 ");
  blk("                                                                ");
  exit(0);
}

//----------------------------------------------------------------
// Procedure: showReleaseInfoAndExit

void showReleaseInfoAndExit()
{
  showReleaseInfo("pTurnInPlace", "gpl");
  exit(0);
}
