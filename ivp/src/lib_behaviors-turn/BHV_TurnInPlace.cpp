/************************************************************/
/*    NAME: Turn-in-place trigger behavior                  */
/*    ORGN: West Point Robotics Research Center             */
/*    FILE: BHV_TurnInPlace.cpp                             */
/*    DATE: 2026                                            */
/************************************************************/

#include <cstdlib>
#include "BHV_TurnInPlace.h"
#include "MBUtils.h"

using namespace std;

//-----------------------------------------------------------
// Constructor

BHV_TurnInPlace::BHV_TurnInPlace(IvPDomain gdomain) : IvPBehavior(gdomain)
{
  m_descriptor = "bhv_turn_in_place";

  m_request_var = "TURN_REQUEST";
  m_done_var    = "TURN_DONE";

  m_have_heading = false;
  m_heading      = 0;
  m_have_delta   = false;
  m_delta        = 0;
  m_heading_var  = "";

  m_requested     = false;
  m_request_count = 0;
  m_request_id    = "";

  // NAV not strictly needed here (the app reads it), but useful for
  // debugging/status and harmless to have in the buffer.
  addInfoVars("NAV_HEADING", "no_warning");
}

//-----------------------------------------------------------
// Procedure: setParam

bool BHV_TurnInPlace::setParam(string param, string val)
{
  if(param == "heading") {
    m_have_heading = true; m_heading = atof(val.c_str()); }
  else if(param == "delta") {
    m_have_delta = true; m_delta = atof(val.c_str()); }
  else if(param == "heading_var")
    m_heading_var = val;
  else if(param == "strategy")     m_p_strategy = val;
  else if(param == "fwd_thrust")   m_p_fwd = val;
  else if(param == "rev_thrust")   m_p_rev = val;
  else if(param == "rudder")       m_p_rudder = val;
  else if(param == "tol")          m_p_tol = val;
  else if(param == "settle")       m_p_settle = val;
  else if(param == "cap")          m_p_cap = val;
  else if(param == "return_frac")  m_p_return_frac = val;
  else if(param == "phase_time")   m_p_phase_time = val;
  else if(param == "request_var")  m_request_var = val;
  else if(param == "done_var")     m_done_var = val;
  else
    return(false);

  return(true);
}

//-----------------------------------------------------------
// Procedure: onSetParamComplete

void BHV_TurnInPlace::onSetParamComplete()
{
  addInfoVars(m_done_var, "no_warning");
  if(m_heading_var != "")
    addInfoVars(m_heading_var, "no_warning");
  postConfigStatus();
}

//-----------------------------------------------------------
// Procedure: onIdleState
//   While idle, keep the trigger disarmed so the next time run
//   conditions are met a fresh maneuver is requested.

void BHV_TurnInPlace::onIdleState()
{
  m_requested = false;
}

void BHV_TurnInPlace::onRunToIdleState()
{
  m_requested = false;
}

//-----------------------------------------------------------
// Procedure: buildRequest
//   Assemble a TURN_REQUEST string (no spaces). Returns "" if the
//   heading spec is unavailable this cycle.

string BHV_TurnInPlace::buildRequest()
{
  string hspec;
  if(m_heading_var != "") {
    bool ok = false;
    double h = getBufferDoubleVal(m_heading_var, ok);
    if(!ok) {
      postWMessage(m_heading_var + " not yet available");
      return("");
    }
    hspec = "heading=" + doubleToStringX(h, 2);
  }
  else if(m_have_delta)
    hspec = "delta=" + doubleToStringX(m_delta, 2);
  else if(m_have_heading)
    hspec = "heading=" + doubleToStringX(m_heading, 2);
  else {
    postEMessage("No heading, delta, or heading_var configured");
    return("");
  }

  m_request_count++;
  m_request_id = m_descriptor + "#" + uintToString(m_request_count);

  string req = hspec + ",id=" + m_request_id;
  if(m_p_strategy    != "") req += ",strategy="    + m_p_strategy;
  if(m_p_fwd         != "") req += ",fwd_thrust="  + m_p_fwd;
  if(m_p_rev         != "") req += ",rev_thrust="  + m_p_rev;
  if(m_p_rudder      != "") req += ",rudder="      + m_p_rudder;
  if(m_p_tol         != "") req += ",tol="         + m_p_tol;
  if(m_p_settle      != "") req += ",settle="      + m_p_settle;
  if(m_p_cap         != "") req += ",cap="         + m_p_cap;
  if(m_p_return_frac != "") req += ",return_frac=" + m_p_return_frac;
  if(m_p_phase_time  != "") req += ",phase_time="  + m_p_phase_time;
  return(req);
}

//-----------------------------------------------------------
// Procedure: onRunState
//   No IvP objective function is produced (returns 0). This behavior
//   only fires the request and waits for completion; the pTurnInPlace
//   app owns the actuators during the maneuver.

IvPFunction* BHV_TurnInPlace::onRunState()
{
  if(!m_requested) {
    string req = buildRequest();
    if(req == "")
      return(0);
    postMessage(m_request_var, req);
    postMessage("TURN_BHV_STATUS", string("requested:") + m_request_id);
    m_requested = true;
    return(0);
  }

  // Awaiting completion. The app posts TURN_DONE=<id> when finished.
  bool ok = false;
  string done = getBufferStringVal(m_done_var, ok);
  if(ok && (done == m_request_id)) {
    postMessage("TURN_BHV_STATUS", string("complete:") + m_request_id);
    setComplete();   // fires the behavior's endflags; mission resumes
  }
  return(0);
}
