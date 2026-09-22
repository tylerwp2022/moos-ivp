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

#include <cstdlib>
#include <string>
#include <FL/Fl.H>
#include <FL/Fl_Text_Editor.H>
#include <FL/Fl_Text_Buffer.H>
#include <FL/fl_draw.H>

// The chat pane's text entry: a word-wrapping editor that grows with
// what is typed, up to a set number of lines, and scrolls past that.
// Enter fires the widget callback (send); Shift+Enter starts a new
// line while composing. When the text needs a different height the
// grow hook is called so the owner can re-lay out the pane.
//
// Two more departures from a stock editor:
//
//  1. It only takes keyboard focus from a mouse click, never from
//     window-level focus navigation (startup, Tab). pMarineViewer's
//     single-key hotkeys live in PMV_GUI::handle(), which only sees
//     keys when no child has focus, so the pane must not grab focus
//     on its own.
//  2. Escape hands focus back to the window so the hotkeys work
//     again after typing.

class PMV_ChatInput : public Fl_Text_Editor {
 public:
  typedef void (*GrowHook)(void*);

  PMV_ChatInput(int x, int y, int w, int h, const char* l=0)
    : Fl_Text_Editor(x, y, w, h, l), m_want_focus(false), m_max_lines(6),
      m_seen_len(0), m_grow_hook(0), m_grow_data(0) {
    m_buff = new Fl_Text_Buffer();
    buffer(m_buff);
    box(FL_DOWN_BOX);
    wrap_mode(Fl_Text_Display::WRAP_AT_BOUNDS, 0);
    scrollbar_align(FL_ALIGN_RIGHT);
    scrollbar_width(12);
  }
  virtual ~PMV_ChatInput() {
    buffer(0);
    delete(m_buff);
  }

  std::string getText() const {
    char* s = m_buff->text();
    std::string out = (s ? s : "");
    free(s);
    return(out);
  }
  void clearText() {
    m_buff->text("");
    m_seen_len = 0;
  }

  void setMaxLines(int n)        {m_max_lines = (n < 1) ? 1 : n;}
  int  getMaxLines() const       {return(m_max_lines);}
  void setGrowHook(GrowHook f, void* data) {m_grow_hook = f; m_grow_data = data;}

  // The height that shows every wrapped line of the text at the given
  // width, capped at the line limit. Wrapping depends on the width,
  // so the widget takes that width first; the caller places it after.
  int wantedHeight(int width) {
    if(w() != width)
      resize(x(), y(), width, h());
    int lines = 1;
    if(m_buff->length() > 0)
      lines = count_lines(0, m_buff->length(), true) + 1;
    if(lines > m_max_lines)
      lines = m_max_lines;
    fl_font(textfont(), textsize());
    return(lines * fl_height() + Fl::box_dh(box()) + 6);
  }

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
      if(((Fl::event_key() == FL_Enter) || (Fl::event_key() == FL_KP_Enter)) &&
	 !(Fl::event_state() & FL_SHIFT)) {
	do_callback();
	return(1);
      }
      break;
    }
    int result = Fl_Text_Editor::handle(event);
    if(m_buff->length() != m_seen_len) {
      m_seen_len = m_buff->length();
      if(m_grow_hook && (wantedHeight(w()) != h()))
	m_grow_hook(m_grow_data);
    }
    return(result);
  }

 protected:
  Fl_Text_Buffer* m_buff;
  bool            m_want_focus;
  int             m_max_lines;
  int             m_seen_len;
  GrowHook        m_grow_hook;
  void*           m_grow_data;
};

#endif
