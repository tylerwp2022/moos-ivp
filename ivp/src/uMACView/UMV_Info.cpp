/*****************************************************************/
/*    NAME: Michael Benjamin                                     */
/*    ORGN: Dept of Mechanical Engineering, MIT, Cambridge MA    */
/*    FILE: UMV_Info.cpp                                         */
/*    DATE: Aug 11th 2012                                        */
/*    MODIFIED: Timeo Williams, 2026-11-24                        */
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
/*                                                               */
/* You should have received a copy of the GNU General Public     */
/* License along with MOOS-IvP.  If not, see                     */
/* <http://www.gnu.org/licenses/>.                               */
/*****************************************************************/
 
#include <cstdlib>
#include <iostream>
#include "ColorParse.h"
#include "ReleaseInfo.h"
#include "UMV_Info.h"

using namespace std;

//----------------------------------------------------------------
// Procedure: showSynopsis

void showSynopsis()
{
  blk("SYNOPSIS:                                                       ");
  blk("------------------------------------                            ");
  blk("  uMACView is a GUI tool for visually monitoring appcasts. It   ");
  blk("  will parse appcasts generated within its own MOOS community or");
  blk("  those from other MOOS communities bridged or shared to the    "); 
  blk("  local MOOSDB. Its capability is nearly identical to the       ");
  blk("  appcast viewing capability built into pMarineViewer. It was   ");
  blk("  intended to be an appcast viewer for non-pMarineViewer users. ");
}

//----------------------------------------------------------------
// Procedure: showHelpAndExit

void showHelpAndExit()
{
  blk("                                                                ");
  blu("=============================================================== ");
  blu("Usage: uMACView file.moos [OPTIONS]                             ");
  blu("=============================================================== ");
  blk("                                                                ");
  showSynopsis();
  blk("                                                                ");
  blk("Options:                                                        ");
  mag("  --alias","=<ProcessName>                                      ");
  blk("      Launch uMACView with the given process name rather        ");
  blk("      than uMACView.                                            ");
  mag("  --example, -e                                                 ");
  blk("      Display example MOOS configuration block.                 ");
  mag("  --help, -h                                                    ");
  blk("      Display this help message.                                ");
  mag("  --interface, -i                                               ");
  blk("      Display MOOS publications and subscriptions.              ");
  mag("  --version,-v                                                  ");
  blk("      Display the release version of uMACView.                  ");
  mag("  --web,-w                                                      ");
  blk("      Open browser to: https://oceanai.mit.edu/ivpman/apps/uMACView ");
  blk("                                                                ");
  blk("Note: If argv[2] does not otherwise match a known option,       ");
  blk("      then it will be interpreted as a run alias. This is       ");
  blk("      to support pAntler launching conventions.                 ");
  blk("                                                                ");
  exit(0);
}

//----------------------------------------------------------------
// Procedure: showExampleConfigAndExit

void showExampleConfigAndExit()
{
  blk("                                                                ");
  blu("=============================================================== ");
  blu("uMACView Example MOOS Configuration                             ");
  blu("=============================================================== ");
  blk("                                                                ");
  blk("ProcessConfig = uMACView                                        ");
  blk("{                                                               ");
  blk("  AppTick   = 4                                                 ");
  blk("  CommsTick = 4                                                 ");
  blk("                                                                ");
  blk("  // Font options xsmall, small, medium, large, xlarge          ");
  blk("                                                                ");
  blk("  procs_font_size    = large   // Default is large              ");
  blk("  nodes_font_size    = large   // Default is large              ");
  blk("  infocast_font_size = medium  // Default is medium             ");
  blk("                                                                ");
  blk("  appcast_color_scheme   = indigo    // {indigo, beige, white}  ");
  blk("  realmcast_color_scheme = hillside  // {hillside, beige, indigo, white}");
  blk("                                                                ");
  blk("  infocast_height      = 70       // [30,35,40,...,85,90]       ");
  blk("  refresh_mode         = events   // {paused, events, streaming}");
  blk("  content_mode         = appcast  // {appcast, realmcast}       ");
  blk("                                                                ");
  blk("  realmcast_show_source = true;          // Default is true     ");
  blk("  realmcast_show_communinity = true;     // Default is true     ");
  blk("  realmcast_show_subscriptions = true;   // Default is true     ");
  blk("  realmcast_show_masked   = true;        // Default is true     ");
  blk("  realmcast_wrap_content  = false;       // Default is false    ");
  blk("  realmcast_trunc_content = false;       // Default is false    ");
  blk("  realmcast_time_format_utc = false      // Default is false    ");
  blk("  // LLM chat pane on the right edge (pairs with pLLMAgent)    ");
  blk("  chat_viewable        = false   // {true, FALSE}               ");
  blk("  chat_width           = 25      // pct of window, {15..60}     ");
  blk("  chat_input_lines     = 6       // input lines max, {1..20}    ");
  blk("  chat_interrupt_var   = LLM_INTERRUPT // Ctrl+C while thinking ");
  blk("                                 // posts here; off to disable  ");
  blk("  chat_plan_var        = BT_CHAT // plan> lines; off to hide;    ");
  blk("                                 // BT_CHAT_* in a fleet: each   ");
  blk("                                 // vehicle's lines, with its name,");
  blk("                                 // and the bare BT_CHAT as well  ");
  blk("  chat_color_you       = auto    // auto or a color name, also   ");
  blk("  chat_color_llm       = auto    // chat_color_ask (a message    ");
  blk("  chat_color_plan      = auto    // waiting on you) and          ");
  blk("  chat_color_warn      = auto    // chat_color_warn (a WARNING   ");
  blk("                                 // line inside a proposal),     ");
  blk("  chat_color_note      = auto    // chat_color_note (a line that ");
  blk("                                 // asks nothing of you, italic) ");
  blk("  // resize live: drag the bar left of the pane, or Ctrl+] / Ctrl+[");
  blk("  chat_in_var          = LLM_CHAT_IN // typed here; a line another");
  blk("                                 // app posts shows as <app>>    ");
  blk("  chat_out_var         = LLM_CHAT_OUT                           ");
  blk("  chat_status_var      = LLM_STATUS                             ");
  blk("  chat_font_size       = 12         // 8..32 points; Ctrl+= and ");
  blk("                                    // Ctrl+- change it live     ");
  blk("  chat_mode_var        = LLM_MODE   // the agent's mode beside   ");
  blk("                                    // the status; planning tints");
  blk("                                    // the line amber; off = none");
  blk("  chat_console_var     = LLM_CONSOLE // the agent's / commands,  ");
  blk("                                    // completed on Tab; off =  ");
  blk("                                    // a built-in list          ");
  blk("                                                                ");
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
  blu("uMACView INTERFACE                                              ");
  blu("=============================================================== ");
  blk("                                                                ");
  showSynopsis();
  blk("                                                                ");
  blk("SUBSCRIPTIONS:                                                  ");
  blk("------------------------------------                            ");
  blk("  APPCAST = proc=pHostInfo!@#iter=48!@#node=shoreside!@#        ");
  blk("            iter=48!@#messages=...                              ");
  blk("  LLM_CHAT_IN = operator input posted by another MOOS app       ");
  blk("  LLM_CHAT_OUT = replies, questions, events, and proposals      ");
  blk("  LLM_STATUS, LLM_MODE, LLM_CONSOLE = state and slash commands  ");
  blk("  BT_CHAT = plan messages (optionally BT_CHAT_* for a fleet)    ");
  blk("                                                                ");
  blk("PUBLICATIONS:                                                   ");
  blk("------------------------------------                            ");
  blk("  LLM_CHAT_IN = text typed in the chat pane                     ");
  blk("  LLM_INTERRUPT = now, on Ctrl+C while the agent is thinking    ");
  blk("  APPACAST_REQ =       node=shoreside,app=any,duration=3.0,     ");
  blk("                       key=pMarineViewer,thresh=run_warning     ");
  blk("  APPACAST_REQ_HENRY = node=henry,app=pHelmIvP,duration=3.0,    ");
  blk("                       key=pMarineViewer,thresh=any             ");
  blk("                                                                ");
  exit(0);
}

//----------------------------------------------------------------
// Procedure: showReleaseInfoAndExit

void showReleaseInfoAndExit()
{
  showReleaseInfo("uMACView", "gpl");
  exit(0);
}









