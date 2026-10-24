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
#include <vector>
#include <map>
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
//  3. Ctrl+C asks the owner's interrupt hook first: while the
//     assistant thinks it interrupts the turn (and the hook puts the
//     line last sent back here to edit); any other time it stays
//     the editor's copy.
//  4. History, as a shell's: the owner adds each line it sends
//     (addHistory); Up with the cursor on the first line of the box
//     recalls the line before, Down on the last line the one after,
//     and past the newest the draft that was being typed. An edit
//     made to a recalled line is kept while browsing, as bash keeps
//     it, until a line is sent. Elsewhere in the text Up and Down
//     move the cursor as usual.

class PMV_ChatInput : public Fl_Text_Editor {
 public:
  typedef void (*GrowHook)(void*);
  typedef bool (*InterruptHook)(void*);   // true: Ctrl+C was taken as an interrupt

  PMV_ChatInput(int x, int y, int w, int h, const char* l=0)
    : Fl_Text_Editor(x, y, w, h, l), m_want_focus(false), m_max_lines(6),
      m_seen_len(0), m_grow_hook(0), m_grow_data(0),
      m_interrupt_hook(0), m_interrupt_data(0), m_hist_pos(0) {
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
  // A line put back into the box (after an interrupt), cursor at its end
  void setText(const std::string& s) {
    m_buff->text(s.c_str());
    m_seen_len = m_buff->length();
    insert_position(m_buff->length());
    show_insert_position();
  }

  // A line sent, remembered for Up/Down: not an empty one, not the
  // same as the newest, not a bare confirmation answer; the newest
  // 200 kept. Browsing starts over past the newest, edits forgotten.
  void addHistory(const std::string& s) {
    std::string low;
    for(unsigned int i=0; i<s.size(); i++)
      low += (char)tolower((unsigned char)s[i]);
    if((s == "") || (low == "y") || (low == "n") || (low == "yes") || (low == "no"))
      return;
    if(m_history.empty() || (m_history.back() != s))
      m_history.push_back(s);
    if(m_history.size() > 200)
      m_history.erase(m_history.begin());
    m_hist_pos = m_history.size();
    m_draft = "";
    m_edits.clear();
  }
  unsigned int historySize() const {return(m_history.size());}

  void setMaxLines(int n)        {m_max_lines = (n < 1) ? 1 : n;}
  int  getMaxLines() const       {return(m_max_lines);}
  void setGrowHook(GrowHook f, void* data) {m_grow_hook = f; m_grow_data = data;}
  void setInterruptHook(InterruptHook f, void* data) {m_interrupt_hook = f; m_interrupt_data = data;}

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
      if((Fl::event_state() & FL_CTRL) && (Fl::event_key() == 'c')) {
	if(m_interrupt_hook && m_interrupt_hook(m_interrupt_data))
	  return(1);
      }
      if(Fl::event_key() == FL_Escape) {
	Fl::focus(window());
	return(1);
      }
      if(((Fl::event_key() == FL_Enter) || (Fl::event_key() == FL_KP_Enter)) &&
	 !(Fl::event_state() & FL_SHIFT)) {
	do_callback();
	return(1);
      }
      if((Fl::event_key() == FL_Up) && onFirstLine() && (m_hist_pos > 0)) {
	recall(m_hist_pos - 1);
	return(1);
      }
      if((Fl::event_key() == FL_Down) && onLastLine() && (m_hist_pos < m_history.size())) {
	recall(m_hist_pos + 1);
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
  // The cursor on the first or the last wrapped line of the text: the
  // visual line holding it starts at the text's start, or ends at its end
  bool onFirstLine() {
    return(line_start(insert_position()) == 0);
  }
  bool onLastLine() {
    return(line_end(insert_position(), false) >= m_buff->length());
  }
  // Move to a history position: what the box holds now is kept for
  // the position left (the draft past the newest, an edit of an
  // entry), the text of the position reached shown with the cursor
  // at its end, and the pane re-laid out when the height changes.
  void recall(unsigned int pos) {
    std::string now = getText();
    if(m_hist_pos == m_history.size())
      m_draft = now;
    else if(now != m_history[m_hist_pos])
      m_edits[m_hist_pos] = now;
    else
      m_edits.erase(m_hist_pos);
    m_hist_pos = pos;
    if(pos == m_history.size())
      setText(m_draft);
    else if(m_edits.count(pos))
      setText(m_edits[pos]);
    else
      setText(m_history[pos]);
    if(m_grow_hook && (wantedHeight(w()) != h()))
      m_grow_hook(m_grow_data);
  }

  Fl_Text_Buffer* m_buff;
  bool            m_want_focus;
  int             m_max_lines;
  int             m_seen_len;
  GrowHook        m_grow_hook;
  void*           m_grow_data;
  InterruptHook   m_interrupt_hook;
  void*           m_interrupt_data;
  std::vector<std::string>            m_history;   // the lines sent, oldest first
  unsigned int                        m_hist_pos;  // where browsing stands; size() = past the newest
  std::string                         m_draft;     // the text left behind when browsing began
  std::map<unsigned int, std::string> m_edits;     // an entry as edited while browsing
};

#endif
