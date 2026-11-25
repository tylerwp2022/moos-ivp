/*****************************************************************/
/*    NAME: Tyler Errico                                         */
/*    ORGN: West Point Robotics Research Center                  */
/*    FILE: LLMChatMail.cpp                                      */
/*    DATE: September 15th, 2026                                 */
/*    MODIFIED: Timeo Williams, 2026-11-24                           */
/*                                                               */
/* This file is part of MOOS-IvP                                 */
/*                                                               */
/* MOOS-IvP is free software: you can redistribute it and/or     */
/* modify it under the terms of the GNU General Public License   */
/* as published by the Free Software Foundation, either version  */
/* 3 of the License, or (at your option) any later version.      */
/*                                                               */
/* MOOS-IvP is distributed in the hope that it will be useful,   */
/* but WITHOUT ANY WARRANTY; without even the implied warranty   */
/* of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See  */
/* the GNU General Public License for more details.              */
/*****************************************************************/

#include "LLMChatMail.h"
#include "MBUtils.h"
#include "MOOS/libMOOS/Comms/MOOSCommClient.h"

using namespace std;

bool LLMChatMail::configure(const string& param, const string& value)
{
  lock_guard<mutex> lock(m_config_mutex);
  if(param == "chat_in_var")
    return setNonWhiteVarOnString(m_input, value);
  if(param == "chat_out_var")
    return setNonWhiteVarOnString(m_output, value);
  if(param == "chat_status_var")
    return setNonWhiteVarOnString(m_status, value);

  string* variable = nullptr;
  if(param == "chat_mode_var")
    variable = &m_mode;
  else if(param == "chat_console_var")
    variable = &m_console;
  else if(param == "chat_plan_var")
    variable = &m_plan;
  else if(param == "chat_interrupt_var")
    variable = &m_interrupt;
  if(!variable)
    return false;
  if(tolower(value) == "off") {
    variable->clear();
    return true;
  }
  return setNonWhiteVarOnString(*variable, value);
}

void LLMChatMail::registerVariables(CMOOSCommClient& comms) const
{
  lock_guard<mutex> lock(m_config_mutex);
  comms.Register(m_input, 0);
  comms.Register(m_output, 0);
  comms.Register(m_status, 0);
  if(!m_mode.empty())
    comms.Register(m_mode, 0);
  if(!m_console.empty())
    comms.Register(m_console, 0);
  if(strEnds(m_plan, "*")) {
    comms.Register(m_plan, "*", 0);
    if(strEnds(m_plan, "_*"))
      comms.Register(m_plan.substr(0, m_plan.size()-2), 0);
  }
  else if(!m_plan.empty())
    comms.Register(m_plan, 0);
}

bool LLMChatMail::handle(CMOOSMsg& msg, const string& viewer, LLMChatPane& pane)
{
  const string& key = msg.GetKey();
  const string& text = msg.GetString();
  const string& aux = msg.GetSourceAux();
  if(key == m_output) {
    if(!acceptTranscript(msg))
      return true;
    if(strBegins(aux, "event"))
      pane.addChatLine("event", text, "plan");
    else {
      string role;
      if(strBegins(aux, "ask"))
        role = "ask";
      else if(strContains(aux, "question"))
        role = "question";
      else if(strContains(aux, "interim") || strBegins(aux, "button") ||
              (aux.empty() && strBegins(text, "[")))
        role = "note";
      pane.addChatLine("llm", text, role);
    }
  }
  else if(key == m_input) {
    // The sender echoes its own input locally. Other operators still see it.
    if(msg.GetSource() != viewer && acceptTranscript(msg))
      pane.addChatLine(msg.GetSource(), text, "you");
  }
  else if(!m_mode.empty() && key == m_mode)
    pane.setChatMode(text);
  else if(!m_console.empty() && key == m_console)
    pane.setChatCommands(text);
  else if(key == m_status)
    pane.setChatStatus(text);
  else {
    if(m_plan.empty())
      return false;

    string body = text;
    if(strEnds(m_plan, "*")) {
      string prefix = m_plan.substr(0, m_plan.size() - 1);
      if(strBegins(key, prefix)) {
        string vehicle = tolower(key.substr(prefix.size()));
        if(!vehicle.empty())
          body = vehicle + ": " + body;
      }
      else if(!strEnds(prefix, "_") || key != prefix.substr(0, prefix.size() - 1))
        return false;
    }
    else if(key != m_plan)
      return false;

    if(acceptTranscript(msg))
      pane.addChatLine("plan", body, strBegins(aux, "ask") ? "ask" : "");
  }
  return true;
}

bool LLMChatMail::acceptTranscript(CMOOSMsg& msg)
{
  // MOOSDB gives new subscriptions the last posted value again after reconnect.
  auto entry = make_tuple(msg.GetTime(), msg.GetSource(), msg.GetString(), msg.GetSourceAux());
  auto previous = m_last_line.find(msg.GetKey());
  if(previous != m_last_line.end() && previous->second == entry)
    return false;
  m_last_line[msg.GetKey()] = entry;
  return true;
}
