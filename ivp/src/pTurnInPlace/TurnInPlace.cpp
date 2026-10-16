/************************************************************/
/*    NAME: Turn-in-place characterization                  */
/*    ORGN: West Point Robotics Research Center             */
/*    FILE: TurnInPlace.cpp                                  */
/*    DATE: 2026                                            */
/************************************************************/

#include <iterator>
#include <cmath>
#include <cstdlib>
#include "MBUtils.h"
#include "AngleUtils.h"
#include "ACTable.h"
#include "TurnInPlace.h"

using namespace std;

//---------------------------------------------------------
// Constructor

TurnInPlace::TurnInPlace()
{
  // Config defaults
  m_strategy       = "kturn";
  m_rudder_max     = 100.0;
  m_fwd_thrust     = 60.0;
  m_rev_thrust     = -60.0;
  m_heading_tol    = 5.0;
  m_settle_time    = 2.0;
  m_footprint_cap  = 6.0;
  m_return_frac    = 0.25;
  m_phase_time     = 3.0;
  m_max_run_time   = 120.0;

  m_thrust_var     = "DESIRED_THRUST";
  m_rudder_var     = "DESIRED_RUDDER";

  // Helm handoff: by default we seize the actuators from the helm/PID
  // for the duration of the maneuver and release them when done. Set
  // manage_override=false in a standalone rig that has no helm/PID.
  m_manage_override = true;
  m_override_var    = "MOOS_MANUAL_OVERRIDE";

  // Nav state
  m_nav_x = 0; m_nav_y = 0; m_nav_heading = 0; m_nav_speed = 0;
  m_got_nav_x = false; m_got_nav_y = false; m_got_nav_hdg = false;

  // Active state
  m_active        = false;
  m_posted_idle   = false;
  m_run_strategy  = "kturn";
  m_trial_id      = "";
  m_target_heading = 0;
  m_station_x = 0; m_station_y = 0;
  m_run_tol = 5.0; m_run_settle = 2.0;
  m_run_fwd = 60.0; m_run_rev = -60.0;
  m_run_rudder = 100.0; m_run_cap = 6.0;
  m_run_return_frac = 0.25; m_run_phase_time = 3.0;
  m_phase_fwd = true;
  m_phase_start = 0;
  m_start_time = 0;
  m_settle_start = -1;
  m_start_heading = 0;

  m_heading_err = 0;
  m_excursion   = 0;
  m_max_excursion = 0;
  m_bbox_minx = 0; m_bbox_maxx = 0; m_bbox_miny = 0; m_bbox_maxy = 0;

  m_trials_done = 0;
  m_last_result = "(none)";
  m_last_warning = "";
}

//---------------------------------------------------------
// Procedure: OnNewMail()

bool TurnInPlace::OnNewMail(MOOSMSG_LIST &NewMail)
{
  AppCastingMOOSApp::OnNewMail(NewMail);

  MOOSMSG_LIST::iterator p;
  for(p=NewMail.begin(); p!=NewMail.end(); p++) {
    CMOOSMsg &msg = *p;
    string key  = msg.GetKey();
    string sval = msg.GetString();
    double dval = msg.GetDouble();

    if(key == "NAV_X")            { m_nav_x = dval; m_got_nav_x = true; }
    else if(key == "NAV_Y")       { m_nav_y = dval; m_got_nav_y = true; }
    else if(key == "NAV_HEADING") { m_nav_heading = dval; m_got_nav_hdg = true; }
    else if(key == "NAV_SPEED")   { m_nav_speed = dval; }
    else if(key == "TURN_REQUEST") handleMailTurnRequest(sval);
    else if(key == "TURN_STOP")   handleMailTurnStop();
  }
  return(true);
}

//---------------------------------------------------------
// Procedure: OnConnectToServer()

bool TurnInPlace::OnConnectToServer()
{
  registerVariables();
  return(true);
}

//---------------------------------------------------------
// Procedure: Iterate()

bool TurnInPlace::Iterate()
{
  AppCastingMOOSApp::Iterate();

  if(m_active)
    runController();
  else if(!m_posted_idle) {
    postActuators(0, 0);       // one clean allstop on transition to idle
    m_posted_idle = true;
  }

  AppCastingMOOSApp::PostReport();
  return(true);
}

//---------------------------------------------------------
// Procedure: handleMailTurnRequest()
//   Parse a comma-separated key=val request and begin a maneuver.
//   Recognized keys (all optional except a heading spec):
//     heading=<abs deg>  OR  delta=<rel deg from current heading>
//     x=,y=      station point (default: current NAV position)
//     strategy=  circle|kturn|shuffle
//     tol=, settle=, fwd_thrust=, rev_thrust=, rudder=,
//     cap=, return_frac=, phase_time=, id=

void TurnInPlace::handleMailTurnRequest(const string& request)
{
  if(!m_got_nav_hdg || !m_got_nav_x || !m_got_nav_y) {
    m_last_warning = "TURN_REQUEST ignored: no NAV data yet";
    return;
  }

  // Start from config defaults, override per-request
  m_run_strategy    = m_strategy;
  m_run_tol         = m_heading_tol;
  m_run_settle      = m_settle_time;
  m_run_fwd         = m_fwd_thrust;
  m_run_rev         = m_rev_thrust;
  m_run_rudder      = m_rudder_max;
  m_run_cap         = m_footprint_cap;
  m_run_return_frac = m_return_frac;
  m_run_phase_time  = m_phase_time;
  m_trial_id        = "trial_" + uintToString(m_trials_done + 1);

  bool   have_heading = false;
  double heading_abs  = m_nav_heading;
  bool   have_station = false;
  double sx = m_nav_x, sy = m_nav_y;

  vector<string> kvs = parseString(request, ',');
  for(unsigned int i=0; i<kvs.size(); i++) {
    string key = tolower(biteStringX(kvs[i], '='));
    string val = kvs[i];
    if(key == "heading") { heading_abs = atof(val.c_str()); have_heading = true; }
    else if(key == "delta") {
      heading_abs = m_nav_heading + atof(val.c_str()); have_heading = true; }
    else if(key == "x") { sx = atof(val.c_str()); have_station = true; }
    else if(key == "y") { sy = atof(val.c_str()); have_station = true; }
    else if(key == "strategy")    m_run_strategy = tolower(val);
    else if(key == "tol")         m_run_tol = atof(val.c_str());
    else if(key == "settle")      m_run_settle = atof(val.c_str());
    else if(key == "fwd_thrust")  m_run_fwd = atof(val.c_str());
    else if(key == "rev_thrust")  m_run_rev = atof(val.c_str());
    else if(key == "rudder")      m_run_rudder = atof(val.c_str());
    else if(key == "cap")         m_run_cap = atof(val.c_str());
    else if(key == "return_frac") m_run_return_frac = atof(val.c_str());
    else if(key == "phase_time")  m_run_phase_time = atof(val.c_str());
    else if(key == "id")          m_trial_id = val;
  }
  (void) have_station;

  if(!have_heading) {
    m_last_warning = "TURN_REQUEST ignored: no heading/delta specified";
    return;
  }

  // Latch the maneuver
  m_target_heading = angle360(heading_abs);
  m_station_x = sx;
  m_station_y = sy;
  m_start_heading = m_nav_heading;
  m_start_time = m_curr_time;
  m_phase_start = m_curr_time;
  m_phase_fwd = true;
  m_settle_start = -1;
  m_max_excursion = 0;
  m_bbox_minx = m_nav_x; m_bbox_maxx = m_nav_x;
  m_bbox_miny = m_nav_y; m_bbox_maxy = m_nav_y;
  m_active = true;
  m_posted_idle = false;
  m_last_warning = "";

  // Seize the actuators: parking the helm makes pMarinePID post a
  // single all-stop and go quiet, so our DESIRED_* posts win uncontested.
  if(m_manage_override)
    Notify(m_override_var, "true");

  postStationMarker();
  Notify("TURN_STATE", "RUNNING");
}

//---------------------------------------------------------
// Procedure: handleMailTurnStop()

void TurnInPlace::handleMailTurnStop()
{
  if(m_active)
    finish(true);
}

//---------------------------------------------------------
// Procedure: runController()
//   One control step of an active maneuver.

void TurnInPlace::runController()
{
  // Derived quantities
  m_heading_err = angle180(m_target_heading - m_nav_heading);
  double dx = m_nav_x - m_station_x;
  double dy = m_nav_y - m_station_y;
  m_excursion = hypot(dx, dy);

  // Metrics
  if(m_excursion > m_max_excursion)
    m_max_excursion = m_excursion;
  if(m_nav_x < m_bbox_minx) m_bbox_minx = m_nav_x;
  if(m_nav_x > m_bbox_maxx) m_bbox_maxx = m_nav_x;
  if(m_nav_y < m_bbox_miny) m_bbox_miny = m_nav_y;
  if(m_nav_y > m_bbox_maxy) m_bbox_maxy = m_nav_y;

  Notify("TURN_HDG_ERR",   m_heading_err);
  Notify("TURN_EXCURSION", m_excursion);

  // Safety timeout
  if((m_curr_time - m_start_time) > m_max_run_time) {
    finish(true);
    return;
  }

  // Done check: heading within tol, held for settle window
  if(fabs(m_heading_err) <= m_run_tol) {
    if(m_settle_start < 0)
      m_settle_start = m_curr_time;
    if((m_curr_time - m_settle_start) >= m_run_settle) {
      finish(false);
      return;
    }
    // Within tol but still settling: coast (no turning torque)
    postActuators(0, 0);
    return;
  }
  m_settle_start = -1;   // left the tol band; reset settle timer

  // Direction we must rotate: +err => increase heading (rudder>0 fwd)
  double sgn = (m_heading_err >= 0) ? 1.0 : -1.0;

  double thrust = 0, rudder = 0;

  if(m_run_strategy == "circle") {
    thrust = m_run_fwd;
    rudder = sgn * m_run_rudder;
  }
  else {  // kturn or shuffle
    // Leg-switching criterion
    if(m_run_strategy == "shuffle") {
      if((m_curr_time - m_phase_start) >= m_run_phase_time) {
        m_phase_fwd = !m_phase_fwd;
        m_phase_start = m_curr_time;
      }
    }
    else {  // kturn: switch on footprint
      if(m_phase_fwd && (m_excursion >= m_run_cap)) {
        m_phase_fwd = false; m_phase_start = m_curr_time;
      }
      else if(!m_phase_fwd && (m_excursion <= (m_run_return_frac * m_run_cap))) {
        m_phase_fwd = true;  m_phase_start = m_curr_time;
      }
    }

    if(m_phase_fwd) {
      thrust = m_run_fwd;
      rudder = sgn * m_run_rudder;
    }
    else {
      // Reverse leg: thrust<0 flips yaw sign, so flip rudder to keep
      // rotating toward the same target heading while backing up.
      thrust = m_run_rev;
      rudder = -sgn * m_run_rudder;
    }
  }

  postActuators(thrust, rudder);
  Notify("TURN_STATE", string("RUNNING:") + (m_phase_fwd ? "FWD" : "REV"));
}

//---------------------------------------------------------
// Procedure: finish()

void TurnInPlace::finish(bool timed_out)
{
  postActuators(0, 0);
  m_active = false;
  m_posted_idle = true;
  m_trials_done++;

  double delta      = fabs(angle180(m_target_heading - m_start_heading));
  double t_elapsed  = m_curr_time - m_start_time;
  double bbox_diag  = hypot(m_bbox_maxx - m_bbox_minx,
                            m_bbox_maxy - m_bbox_miny);
  double final_hdg  = angle180(m_target_heading - m_nav_heading);
  double final_pos  = hypot(m_nav_x - m_station_x, m_nav_y - m_station_y);

  string r;
  r += "id=" + m_trial_id;
  r += ",strategy=" + m_run_strategy;
  r += ",delta="        + doubleToStringX(delta, 2);
  r += ",t_elapsed="    + doubleToStringX(t_elapsed, 2);
  r += ",max_excursion="+ doubleToStringX(m_max_excursion, 2);
  r += ",bbox_diag="    + doubleToStringX(bbox_diag, 2);
  r += ",final_pos_err="+ doubleToStringX(final_pos, 2);
  r += ",final_hdg_err="+ doubleToStringX(final_hdg, 2);
  r += ",timed_out="    + string(timed_out ? "true" : "false");

  Notify("TURN_RESULT", r);
  Notify("TURN_STATE", timed_out ? "TIMEOUT" : "DONE");
  Notify("TURN_DONE", m_trial_id);
  m_last_result = r;

  // Release the actuators back to the helm/PID.
  if(m_manage_override)
    Notify(m_override_var, "false");
}

//---------------------------------------------------------
// Procedure: postActuators()

void TurnInPlace::postActuators(double thrust, double rudder)
{
  if(rudder >  100) rudder =  100;
  if(rudder < -100) rudder = -100;
  if(thrust >  100) thrust =  100;
  if(thrust < -100) thrust = -100;
  Notify(m_thrust_var, thrust);
  Notify(m_rudder_var, rudder);
}

//---------------------------------------------------------
// Procedure: postStationMarker()

void TurnInPlace::postStationMarker()
{
  string pt = "x=" + doubleToStringX(m_station_x, 2) +
              ",y=" + doubleToStringX(m_station_y, 2) +
              ",vertex_size=6,vertex_color=yellow,label=turn_station";
  Notify("VIEW_POINT", pt);
}

//---------------------------------------------------------
// Procedure: OnStartUp()

bool TurnInPlace::OnStartUp()
{
  AppCastingMOOSApp::OnStartUp();

  STRING_LIST sParams;
  m_MissionReader.EnableVerbatimQuoting(false);
  m_MissionReader.GetConfiguration(GetAppName(), sParams);

  STRING_LIST::iterator p;
  for(p=sParams.begin(); p!=sParams.end(); p++) {
    string orig  = *p;
    string line  = *p;
    string param = tolower(biteStringX(line, '='));
    string value = line;

    bool handled = false;
    if(param == "strategy") { m_strategy = tolower(value); handled = true; }
    else if(param == "rudder_max")    handled = setDoubleOnString(m_rudder_max, value);
    else if(param == "fwd_thrust")    handled = setDoubleOnString(m_fwd_thrust, value);
    else if(param == "rev_thrust")    handled = setDoubleOnString(m_rev_thrust, value);
    else if(param == "heading_tol")   handled = setPosDoubleOnString(m_heading_tol, value);
    else if(param == "settle_time")   handled = setPosDoubleOnString(m_settle_time, value);
    else if(param == "footprint_cap") handled = setPosDoubleOnString(m_footprint_cap, value);
    else if(param == "return_frac")   handled = setPosDoubleOnString(m_return_frac, value);
    else if(param == "phase_time")    handled = setPosDoubleOnString(m_phase_time, value);
    else if(param == "max_run_time")  handled = setPosDoubleOnString(m_max_run_time, value);
    else if(param == "thrust_var") { m_thrust_var = value; handled = true; }
    else if(param == "rudder_var") { m_rudder_var = value; handled = true; }
    else if(param == "manage_override") handled = setBooleanOnString(m_manage_override, value);
    else if(param == "override_var") { m_override_var = value; handled = true; }

    if(!handled)
      reportUnhandledConfigWarning(orig);
  }

  registerVariables();
  return(true);
}

//---------------------------------------------------------
// Procedure: registerVariables()

void TurnInPlace::registerVariables()
{
  AppCastingMOOSApp::RegisterVariables();
  Register("NAV_X", 0);
  Register("NAV_Y", 0);
  Register("NAV_HEADING", 0);
  Register("NAV_SPEED", 0);
  Register("TURN_REQUEST", 0);
  Register("TURN_STOP", 0);
}

//---------------------------------------------------------
// Procedure: buildReport()

bool TurnInPlace::buildReport()
{
  m_msgs << "Config defaults" << endl;
  m_msgs << "  strategy=" << m_strategy
         << "  rudder_max=" << doubleToStringX(m_rudder_max,1)
         << "  fwd/rev thrust=" << doubleToStringX(m_fwd_thrust,1)
         << "/" << doubleToStringX(m_rev_thrust,1) << endl;
  m_msgs << "  heading_tol=" << doubleToStringX(m_heading_tol,1)
         << "  settle=" << doubleToStringX(m_settle_time,1)
         << "  cap=" << doubleToStringX(m_footprint_cap,1)
         << "  phase_time=" << doubleToStringX(m_phase_time,1) << endl;
  m_msgs << "  manage_override=" << (m_manage_override ? "true" : "false")
         << " (" << m_override_var << ")" << endl;
  m_msgs << endl;

  m_msgs << "Nav" << endl;
  m_msgs << "  x=" << doubleToStringX(m_nav_x,2)
         << "  y=" << doubleToStringX(m_nav_y,2)
         << "  hdg=" << doubleToStringX(m_nav_heading,1)
         << "  spd=" << doubleToStringX(m_nav_speed,2) << endl;
  m_msgs << endl;

  m_msgs << "Maneuver" << endl;
  if(m_active) {
    m_msgs << "  ACTIVE (" << m_run_strategy << ", "
           << (m_phase_fwd ? "FWD" : "REV") << " leg)" << endl;
    m_msgs << "  target_hdg=" << doubleToStringX(m_target_heading,1)
           << "  hdg_err=" << doubleToStringX(m_heading_err,1) << endl;
    m_msgs << "  excursion=" << doubleToStringX(m_excursion,2)
           << "  max_excursion=" << doubleToStringX(m_max_excursion,2) << endl;
    m_msgs << "  t_elapsed=" << doubleToStringX(m_curr_time-m_start_time,1) << endl;
  }
  else
    m_msgs << "  IDLE" << endl;
  m_msgs << endl;

  m_msgs << "Trials completed: " << m_trials_done << endl;
  m_msgs << "Last result: " << m_last_result << endl;
  if(m_last_warning != "")
    m_msgs << "NOTE: " << m_last_warning << endl;

  return(true);
}
