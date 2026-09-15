/*****************************************************************/
/*    NAME: Tyler Errico                                         */
/*    ORGN: West Point Robotics Research Center                  */
/*    FILE: PMV_ChatSplitter.h                                   */
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

#ifndef PMV_CHAT_SPLITTER_HEADER
#define PMV_CHAT_SPLITTER_HEADER

#include <FL/Fl.H>
#include <FL/Fl_Box.H>
#include <FL/fl_draw.H>

// The thin vertical bar between the map and the chat pane. Dragging
// it fires the widget callback on every mouse move; PMV_GUI reads
// Fl::event_x() there and re-lays out the pane at the new width.

class PMV_ChatSplitter : public Fl_Box {
 public:
  PMV_ChatSplitter(int x, int y, int w, int h)
    : Fl_Box(x, y, w, h) {
    box(FL_FLAT_BOX);
    color(FL_DARK2);
    clear_visible_focus();
  }
  virtual ~PMV_ChatSplitter() {}

  int handle(int event) {
    switch(event) {
    case FL_ENTER:
      fl_cursor(FL_CURSOR_WE);
      return(1);
    case FL_LEAVE:
      fl_cursor(FL_CURSOR_DEFAULT);
      return(1);
    case FL_PUSH:
      return(1);
    case FL_DRAG:
      do_callback();
      return(1);
    case FL_RELEASE:
      return(1);
    }
    return(Fl_Box::handle(event));
  }
};

#endif
