/************************************************************/
/*    NAME: Turn-in-place trigger behavior                  */
/*    ORGN: West Point Robotics Research Center             */
/*    FILE: BHV_TurnInPlace.h                               */
/*    DATE: 2026                                            */
/*                                                          */
/*  Helm-native trigger for a turn-in-place maneuver. This  */
/*  behavior does NOT actuate the vehicle itself -- the      */
/*  reverse K-turn/shuffle cannot be expressed as a helm     */
/*  course/speed objective (reverse is outside the speed     */
/*  domain and needs coordinated rudder/thrust sign flips).  */
/*  Instead, when its run conditions are met it posts a      */
/*  single TURN_REQUEST to the pTurnInPlace app, which seizes */
/*  the actuators via MOOS_MANUAL_OVERRIDE (parking the helm),*/
/*  performs the maneuver, and releases control. This        */
/*  behavior then watches TURN_DONE and calls setComplete()  */
/*  so its endflags fire and the mission resumes.            */
/************************************************************/

#ifndef BHV_TURN_IN_PLACE_HEADER
#define BHV_TURN_IN_PLACE_HEADER

#include <string>
#include "IvPBehavior.h"

class BHV_TurnInPlace : public IvPBehavior {
public:
  BHV_TurnInPlace(IvPDomain);
  ~BHV_TurnInPlace() {}

  bool         setParam(std::string, std::string);
  void         onSetParamComplete();
  void         onIdleState();
  void         onRunToIdleState();
  IvPFunction* onRunState();

protected:
  std::string  buildRequest();

private: // Configuration
  std::string  m_request_var;   // TURN_REQUEST
  std::string  m_done_var;      // TURN_DONE

  // Heading spec (priority: heading_var > delta > heading)
  bool         m_have_heading;
  double       m_heading;
  bool         m_have_delta;
  double       m_delta;
  std::string  m_heading_var;   // read absolute target from this MOOS var

  // Passthrough maneuver params (empty = use app default)
  std::string  m_p_strategy;
  std::string  m_p_fwd;
  std::string  m_p_rev;
  std::string  m_p_rudder;
  std::string  m_p_tol;
  std::string  m_p_settle;
  std::string  m_p_cap;
  std::string  m_p_return_frac;
  std::string  m_p_phase_time;

private: // State
  bool         m_requested;
  unsigned int m_request_count;
  std::string  m_request_id;
};

#define IVP_EXPORT_FUNCTION
extern "C" {
  IVP_EXPORT_FUNCTION IvPBehavior * createBehavior(std::string name, IvPDomain domain)
  {return new BHV_TurnInPlace(domain);}
}

#endif
