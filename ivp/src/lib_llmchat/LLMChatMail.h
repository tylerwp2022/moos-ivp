/*****************************************************************/
/*    NAME: Tyler Errico                                         */
/*    ORGN: West Point Robotics Research Center                  */
/*    FILE: LLMChatMail.h                                      */
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

#ifndef LLM_CHAT_MAIL_HEADER
#define LLM_CHAT_MAIL_HEADER

#include <map>
#include <mutex>
#include <string>
#include <tuple>
#include "LLMChatPane.h"

class CMOOSCommClient;
class CMOOSMsg;

class LLMChatMail {
 public:
  bool configure(const std::string& param, const std::string& value);
  void registerVariables(CMOOSCommClient&) const;
  bool handle(CMOOSMsg&, const std::string& viewer, LLMChatPane&);

  const std::string& inputVar() const {return m_input;}
  const std::string& interruptVar() const {return m_interrupt;}

 private:
  bool acceptTranscript(CMOOSMsg&);
  std::map<std::string, std::tuple<double, std::string, std::string, std::string>> m_last_line;

  // Startup settings and MOOS reconnect registration can run on different threads.
  mutable std::mutex m_config_mutex;
  std::string m_input = "LLM_CHAT_IN";
  std::string m_output = "LLM_CHAT_OUT";
  std::string m_status = "LLM_STATUS";
  std::string m_mode = "LLM_MODE";
  std::string m_console = "LLM_CONSOLE";
  std::string m_plan = "BT_CHAT";
  std::string m_interrupt = "LLM_INTERRUPT";
};

#endif
