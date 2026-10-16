/************************************************************/
/*    NAME: Turn-in-place characterization                  */
/*    ORGN: West Point Robotics Research Center             */
/*    FILE: TurnInPlace.h                                    */
/*    DATE: 2026                                            */
/*                                                          */
/*  Reorient-in-place controller / characterization driver. */
/*  Drives DESIRED_RUDDER + DESIRED_THRUST directly (no helm,*/
/*  no PID) to rotate a rudder-steered surface craft to a    */
/*  commanded compass heading while holding position within  */
/*  a tolerance. Implements several turning "modalities" so  */
/*  the speed-vs-footprint tradeoff can be measured:         */
/*                                                           */
/*    circle  - continuous forward min-radius arc            */
/*    kturn   - forward arc / reverse arc alternation,       */
/*              switching legs on a footprint cap. Reverse    */
/*              rotates the SAME way (rudder sign flipped),   */
/*              so translation cancels while heading advances.*/
/*    shuffle - kturn with time-boxed legs (tight box)       */
/*                                                           */
/*  NOTE ON SIM MODEL: reverse-rotation works in the legacy  */
/*  uSimMarine (dep_uSimMarine) turn model, where turn_rate  */
/*  is constant and the sign of DESIRED_THRUST flips the yaw  */
/*  direction. It does NOT work in uSimMarineV23, whose      */
/*  TurnSpeedMap returns zero turn-rate for speed <= 0. Run   */
/*  this rig against uSimMarine (dep), matching V2GPM.        */
/************************************************************/

#ifndef TURN_IN_PLACE_HEADER
#define TURN_IN_PLACE_HEADER

#include <string>
#include <list>
#include "MOOS/libMOOS/Thirdparty/AppCasting/AppCastingMOOSApp.h"

class TurnInPlace : public AppCastingMOOSApp
{
 public:
  TurnInPlace();
  ~TurnInPlace() {}

 protected: // Standard MOOSApp / AppCasting
  bool OnNewMail(MOOSMSG_LIST &NewMail);
  bool Iterate();
  bool OnConnectToServer();
  bool OnStartUp();
  void registerVariables();
  bool buildReport();

 protected: // Implementation
  void   handleMailTurnRequest(const std::string& request);
  void   handleMailTurnStop();
  void   runController();          // called each Iterate while active
  void   finish(bool timed_out);   // post metrics, go idle
  void   postActuators(double thrust, double rudder);
  void   postStationMarker();

 private: // Configuration (defaults; overridable per-request)
  std::string m_strategy;          // circle | kturn | shuffle
  double m_rudder_max;             // deg-equivalent, [0,100]
  double m_fwd_thrust;             // > 0
  double m_rev_thrust;             // < 0
  double m_heading_tol;            // deg
  double m_settle_time;            // s heading must be held within tol
  double m_footprint_cap;          // m; kturn leg-switch threshold
  double m_return_frac;            // reverse until excursion <= frac*cap
  double m_phase_time;             // s; shuffle leg duration
  double m_max_run_time;           // s; safety timeout per maneuver

 private: // MOOS var names
  std::string m_thrust_var;        // DESIRED_THRUST
  std::string m_rudder_var;        // DESIRED_RUDDER

 private: // Helm handoff
  bool        m_manage_override;   // assert/clear MOOS_MANUAL_OVERRIDE
  std::string m_override_var;      // MOOS_MANUAL_OVERRIDE

 private: // Nav state
  double m_nav_x, m_nav_y, m_nav_heading, m_nav_speed;
  bool   m_got_nav_x, m_got_nav_y, m_got_nav_hdg;

 private: // Active-maneuver state
  bool   m_active;
  bool   m_posted_idle;
  std::string m_run_strategy;      // effective strategy this run
  std::string m_trial_id;
  double m_target_heading;         // absolute deg
  double m_station_x, m_station_y;
  double m_run_tol, m_run_settle, m_run_fwd, m_run_rev;
  double m_run_rudder, m_run_cap, m_run_return_frac, m_run_phase_time;
  bool   m_phase_fwd;              // true=FWD leg, false=REV leg
  double m_phase_start;            // time of current leg start
  double m_start_time;
  double m_settle_start;           // -1 when not currently within tol
  double m_start_heading;

  // Live/derived
  double m_heading_err;
  double m_excursion;

  // Metrics accumulated over the run
  double m_max_excursion;
  double m_bbox_minx, m_bbox_maxx, m_bbox_miny, m_bbox_maxy;

 private: // Appcast bookkeeping
  unsigned int m_trials_done;
  std::string  m_last_result;
  std::string  m_last_warning;
};

#endif
