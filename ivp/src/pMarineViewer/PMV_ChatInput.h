/*****************************************************************/
/*    NAME: Tyler Errico                                         */
/*    ORGN: West Point Robotics Research Center                  */
/*    FILE: PMV_ChatInput.h                                      */
/*    DATE: September 15th, 2026                                 */
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

#ifndef PMV_CHAT_INPUT_HEADER
#define PMV_CHAT_INPUT_HEADER

#include <FL/Fl.H>
#include <FL/Fl_Input.H>

// The chat pane's text entry. Two departures from a stock Fl_Input:
//
//  1. It only takes keyboard focus from a mouse click, never from
//     window-level focus navigation (startup, Tab). pMarineViewer's
//     single-key hotkeys live in PMV_GUI::handle(), which only sees
//     keys when no child has focus, so the pane must not grab focus
//     on its own.
//  2. Escape hands focus back to the window so the hotkeys work
//     again after typing.

class PMV_ChatInput : public Fl_Input {
 public:
  PMV_ChatInput(int x, int y, int w, int h, const char* l=0)
    : Fl_Input(x, y, w, h, l), m_want_focus(false) {}
  virtual ~PMV_ChatInput() {}

  int handle(int event) {
    switch(event) {
    case FL_PUSH:
      m_want_focus = true;
      break;
    case FL_FOCUS:
      if(!m_want_focus)
	return(0);
      m_want_focus = false;
      break;
    case FL_KEYDOWN:
      if(Fl::event_key() == FL_Escape) {
	Fl::focus(window());
	return(1);
      }
      break;
    }
    return(Fl_Input::handle(event));
  }

 protected:
  bool m_want_focus;
};

#endif
