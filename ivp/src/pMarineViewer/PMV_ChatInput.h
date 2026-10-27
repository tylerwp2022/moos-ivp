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
//  5. Tab completes a console command, as a shell does: when the
//     box holds a single word starting with / the commands that
//     begin with it are looked up (setCommands, from the agent's
//     LLM_CONSOLE line "/steps [play [block]], /preview <play>, ...";
//     a built-in list until that arrives); one match fills the word
//     in with a blank after it, several fill in what they share and
//     name the candidates through the hint hook (the owner shows
//     them on the status row for a moment), none says so. With a
//     blank already in the line, Tab shows the command's argument
//     hint instead. Any other Tab is the editor's.

class PMV_ChatInput : public Fl_Text_Editor {
 public:
  typedef void (*GrowHook)(void*);
  typedef bool (*InterruptHook)(void*);   // true: Ctrl+C was taken as an interrupt
  typedef void (*HintHook)(void*, const std::string&);   // a line for the status row, briefly

  PMV_ChatInput(int x, int y, int w, int h, const char* l=0)
    : Fl_Text_Editor(x, y, w, h, l), m_want_focus(false), m_max_lines(6),
      m_seen_len(0), m_grow_hook(0), m_grow_data(0),
      m_interrupt_hook(0), m_interrupt_data(0), m_hist_pos(0),
      m_hint_hook(0), m_hint_data(0) {
    m_buff = new Fl_Text_Buffer();
    buffer(m_buff);
    box(FL_DOWN_BOX);
    wrap_mode(Fl_Text_Display::WRAP_AT_BOUNDS, 0);
    scrollbar_align(FL_ALIGN_RIGHT);
    scrollbar_width(12);
    // pLLMAgent's commands as of this writing, until its own line arrives
    setCommands("/help, /execution, /planning, /review, /mode [execution|planning|review], "
		"/tree [play [block]], /steps [play [block]], /math [play [block]], "
		"/preview <play>, /test <play> <block> [on <boat>] [PORT=value] [limit=<s>], "
		"/alerts [on|off|quiet], /mute <words>, /unmute <words>|all, /muted, /hull on|off");
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
  void setHintHook(HintHook f, void* data) {m_hint_hook = f; m_hint_data = data;}

  // The console's commands for Tab: a comma-separated line, each
  // entry the command word (with its /) then its argument hint, as
  // pLLMAgent posts it on LLM_CONSOLE. An entry without a / is
  // given one. An empty line leaves the list as it is.
  void setCommands(const std::string& line) {
    std::vector<std::pair<std::string, std::string> > cmds;
    std::string rest = line;
    while(rest != "") {
      std::string entry;
      size_t comma = rest.find(',');
      if(comma == std::string::npos) {
	entry = rest;
	rest = "";
      }
      else {
	entry = rest.substr(0, comma);
	rest = rest.substr(comma + 1);
      }
      entry = trim(entry);
      if(entry == "")
	continue;
      std::string word = entry, hint;
      size_t blank = entry.find(' ');
      if(blank != std::string::npos) {
	word = entry.substr(0, blank);
	hint = trim(entry.substr(blank + 1));
      }
      if(word[0] != '/')
	word = "/" + word;
      cmds.push_back(std::make_pair(lower(word), hint));
    }
    if(!cmds.empty())
      m_commands = cmds;
  }
  unsigned int commandCount() const {return(m_commands.size());}

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
      if((Fl::event_key() == FL_Tab) && !(Fl::event_state() & (FL_CTRL | FL_ALT | FL_META))) {
	if(complete())
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

  // Tab on a line starting with /: see the class comment. False when
  // the line is not a command, so the editor keeps the key.
  bool complete() {
    std::string text = getText();
    std::string t = trim(text);
    if((t == "") || (t[0] != '/'))
      return(false);
    size_t blank = t.find_first_of(" \n");
    if(blank != std::string::npos) {
      // a command with arguments: its hint
      std::string word = lower(t.substr(0, blank));
      for(unsigned int i=0; i<m_commands.size(); i++)
	if(m_commands[i].first == word) {
	  hint(word + ((m_commands[i].second == "") ? " takes no argument" : " " + m_commands[i].second));
	  return(true);
	}
      hint("no command " + word);
      return(true);
    }
    std::string typed = lower(t);
    std::vector<unsigned int> hits;
    for(unsigned int i=0; i<m_commands.size(); i++)
      if(m_commands[i].first.compare(0, typed.size(), typed) == 0)
	hits.push_back(i);
    if(hits.empty()) {
      hint("no command starts with " + typed);
      return(true);
    }
    if(hits.size() == 1) {
      setText(m_commands[hits[0]].first + " ");
      std::string h = m_commands[hits[0]].second;
      if(h != "")
	hint(m_commands[hits[0]].first + " " + h);
      return(true);
    }
    // several: what they share, then the candidates
    std::string common = m_commands[hits[0]].first;
    std::string names;
    for(unsigned int k=0; k<hits.size(); k++) {
      const std::string& w = m_commands[hits[k]].first;
      unsigned int n = 0;
      while((n < common.size()) && (n < w.size()) && (common[n] == w[n]))
	n++;
      common = common.substr(0, n);
      names += ((k == 0) ? "" : "  ") + w;
    }
    if(common.size() > typed.size())
      setText(common);
    hint(names);
    return(true);
  }
  void hint(const std::string& s) {
    if(m_hint_hook)
      m_hint_hook(m_hint_data, s);
  }
  static std::string trim(const std::string& s) {
    size_t a = s.find_first_not_of(" \t\r\n");
    if(a == std::string::npos)
      return("");
    size_t b = s.find_last_not_of(" \t\r\n");
    return(s.substr(a, b - a + 1));
  }
  static std::string lower(const std::string& s) {
    std::string out;
    for(unsigned int i=0; i<s.size(); i++)
      out += (char)tolower((unsigned char)s[i]);
    return(out);
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
  HintHook        m_hint_hook;
  void*           m_hint_data;
  std::vector<std::pair<std::string, std::string> > m_commands;  // the / commands and their argument hints
};

#endif
