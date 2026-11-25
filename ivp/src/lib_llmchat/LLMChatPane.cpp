/*****************************************************************/
/*    NAME: Tyler Errico                                         */
/*    ORGN: West Point Robotics Research Center                  */
/*    FILE: LLMChatPane.cpp                                      */
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

#include "LLMChatPane.h"
#include "MBUtils.h"
#include "ColorPack.h"
#include "ColorParse.h"
#include <algorithm>
#include <FL/Fl_Window.H>

using namespace std;

LLMChatPane::LLMChatPane(function<void()> relayout) : m_relayout(relayout)
{
  // Configure the LLM chat pane widgets (placed in resizeWidgets)
  m_chat_viewable = false;
  m_chat_width    = 0.25;
  m_chat_thinking      = false;

  m_chat_buff = new Fl_Text_Buffer();
  m_chat_disp = new Fl_Text_Display(0, 0, 1, 1);
  m_chat_disp->buffer(m_chat_buff);
  m_chat_disp->wrap_mode(Fl_Text_Display::WRAP_AT_BOUNDS, 0);
  m_chat_disp->textfont(FL_COURIER);
  m_chat_font_size = 12;
  m_chat_disp->textsize(m_chat_font_size);
  m_chat_disp->box(FL_DOWN_BOX);
  m_chat_disp->clear_visible_focus();

  // Lines are colored by role through a parallel style buffer: A is
  // the operator, B the model, C anything waiting on the operator,
  // D the running plan, E a WARNING line inside a proposal, F a note
  // that asks nothing of the operator (an update on the way, a console
  // line, a press line: muted, italic). Colors are set in
  // applyChatColors() once the pane's background is known.
  m_chat_style = new Fl_Text_Buffer();
  for(int i=0; i<6; i++) {
    m_chat_colors[i]       = "auto";
    m_chat_styles[i].color = FL_BLACK;
    m_chat_styles[i].font  = (i == 5) ? FL_COURIER_ITALIC : FL_COURIER;
    m_chat_styles[i].size  = m_chat_font_size;
    m_chat_styles[i].attr  = 0;
  }
  m_chat_disp->highlight_data(m_chat_style, m_chat_styles, 6, 'A', 0, 0);

  m_chat_status = new Fl_Output(0, 0, 1, 1);
  m_chat_status->textsize(m_chat_font_size - 1);
  m_chat_status->value("llm: idle");
  m_chat_status->clear_visible_focus();
  m_chat_status_text = "idle";
  m_chat_mode        = "execution";
  m_chat_status_back = FL_BACKGROUND_COLOR;
  m_chat_status_fore = FL_FOREGROUND_COLOR;

  m_chat_input = new LLMChatInput(0, 0, 1, 1);
  m_chat_input->textfont(FL_COURIER);
  m_chat_input->callback(send, this);
  m_chat_input->setGrowHook(grow, this);
  m_chat_input->setInterruptHook(interrupt, this);
  m_chat_input->setHintHook(hint, this);

  m_chat_split = new LLMChatSplitter(0, 0, 1, 1);
  m_chat_split->callback(drag, this);

}

LLMChatPane::~LLMChatPane()
{
  Fl::remove_timeout(clearHint, this);
  delete m_chat_split;
  delete m_chat_input;
  delete m_chat_status;
  delete m_chat_disp;
  delete m_chat_style;
  delete m_chat_buff;
}

void LLMChatPane::addMenu(Fl_Menu_Bar& menu, const string& prefix)
{
  menu.add((prefix + "Toggle Chat Pane").c_str(), FL_CTRL+'t', toggle, this);
  menu.add((prefix + "Chat Pane Wider").c_str(), FL_CTRL+']', wider, this);
  menu.add((prefix + "Chat Text Larger").c_str(), FL_CTRL+'=', larger, this);
  menu.add((prefix + "Chat Text Smaller").c_str(), FL_CTRL+'-', smaller, this);
  menu.add((prefix + "Chat Pane Narrower").c_str(), FL_CTRL+'[', narrower, this,
           FL_MENU_DIVIDER);
}

bool LLMChatPane::configure(const string& param, const string& value)
{
  if(param == "chat_viewable")
    return setChatViewable(value);
  if(param == "chat_width")
    return setChatWidth(value);
  if(param == "chat_input_lines")
    return setChatInputLines(value);
  if(param == "chat_font_size")
    return setChatFontSize(value);
  if(strBegins(param, "chat_color_"))
    return setChatColor(param.substr(11), value);
  return false;
}

namespace {
const int split_width = 6;
}

int LLMChatPane::reservedWidth(int window_width, int available_width, int min_content) const
{
  if(!m_chat_viewable)
    return 0;

  int width = max(280, static_cast<int>(window_width * m_chat_width));
  int available = available_width - min_content - split_width;
  return available > 0 ? min(width, available) + split_width : 0;
}

void LLMChatPane::layout(int window_width, int cy, int reserved_width, int ch,
                         Fl_Color color_back, Fl_Color color_text)
{
  if(reserved_width > split_width) {
    int cw = reserved_width - split_width;
    int cx = window_width - cw;
    // The status row is as tall as its text needs (20 px at the
    // default size); the transcript gives up the difference
    fl_font(m_chat_status->textfont(), m_chat_status->textsize());
    int status_hgt = fl_height() + Fl::box_dh(m_chat_status->box());
    if(status_hgt < 20)
      status_hgt = 20;
    int input_hgt  = m_chat_input->wantedHeight(cw);
    if(input_hgt > (ch / 2))
      input_hgt = ch / 2;
    m_chat_disp->resize(cx, cy, cw, ch - status_hgt - input_hgt);
    m_chat_status->resize(cx, cy + ch - status_hgt - input_hgt, cw, status_hgt);
    m_chat_input->resize(cx, cy + ch - input_hgt, cw, input_hgt);
    m_chat_split->resize(cx - split_width, cy, split_width, ch);
    m_chat_disp->color(color_back);
    m_chat_disp->textcolor(color_text);
    applyChatColors(color_back, color_text);
    m_chat_status_back = color_back;
    m_chat_status_fore = color_text;
    renderChatStatus();
    m_chat_input->color(color_back);
    m_chat_input->textcolor(color_text);
    m_chat_input->cursor_color(color_text);
    m_chat_disp->show();
    m_chat_status->show();
    m_chat_input->show();
    m_chat_split->show();
  }
  else {
    m_chat_disp->hide();
    m_chat_status->hide();
    m_chat_input->hide();
    m_chat_split->hide();
  }
}

void LLMChatPane::send(Fl_Widget*, void* data)
{
  static_cast<LLMChatPane*>(data)->sendMessage();
}

void LLMChatPane::sendMessage()
{
  string text = stripBlankEnds(findReplace(m_chat_input->getText(), "\n", " "));
  if(!text.empty() && (!m_post || !m_post(Post::Message, text))) {
    hint(this, "Chat send failed. Draft kept in the input.");
    return;
  }

  m_chat_input->addHistory(text);
  m_chat_input->clearText();
  if(m_chat_input->wantedHeight(m_chat_input->w()) != m_chat_input->h())
    m_relayout();
  if(!text.empty()) {
    m_chat_last_sent = text;
    addChatLine("you", text);
  }
}

bool LLMChatPane::interrupt(void* data)
{
  return static_cast<LLMChatPane*>(data)->interruptTurn();
}

bool LLMChatPane::interruptTurn()
{
  if(!m_chat_thinking || !m_post || !m_post(Post::Interrupt, "now"))
    return false;

  if(!m_chat_last_sent.empty() && stripBlankEnds(m_chat_input->getText()).empty()) {
    m_chat_input->setText(m_chat_last_sent);
    if(m_chat_input->wantedHeight(m_chat_input->w()) != m_chat_input->h())
      m_relayout();
  }
  return true;
}

void LLMChatPane::hint(void* data, const string& text)
{
  auto* pane = static_cast<LLMChatPane*>(data);
  pane->m_chat_hint = text;
  pane->renderChatStatus();
  Fl::remove_timeout(clearHint, data);
  Fl::add_timeout(4.0, clearHint, data);
}

void LLMChatPane::clearHint(void* data)
{
  auto* pane = static_cast<LLMChatPane*>(data);
  pane->m_chat_hint.clear();
  pane->renderChatStatus();
}

void LLMChatPane::setChatCommands(string line)
{
  m_chat_input->setCommands(line);
}

void LLMChatPane::toggle(Fl_Widget*, void* data)
{
  auto* pane = static_cast<LLMChatPane*>(data);
  pane->setChatViewable("toggle");
  pane->m_relayout();
}

void LLMChatPane::wider(Fl_Widget*, void* data)
{
  static_cast<LLMChatPane*>(data)->adjustChatWidth(5);
}

void LLMChatPane::narrower(Fl_Widget*, void* data)
{
  static_cast<LLMChatPane*>(data)->adjustChatWidth(-5);
}

void LLMChatPane::larger(Fl_Widget*, void* data)
{
  static_cast<LLMChatPane*>(data)->adjustChatFontSize(2);
}

void LLMChatPane::smaller(Fl_Widget*, void* data)
{
  static_cast<LLMChatPane*>(data)->adjustChatFontSize(-2);
}

void LLMChatPane::adjustChatWidth(double delta)
{
  setChatWidth(doubleToString(m_chat_width * 100 + delta, 2));
  m_relayout();
}

void LLMChatPane::drag(Fl_Widget* widget, void* data)
{
  auto* pane = static_cast<LLMChatPane*>(data);
  int width = widget->window()->w();
  double new_width = width - Fl::event_x() - split_width / 2.0;
  pane->setChatWidth(doubleToString(100 * new_width / width, 2));
  pane->m_relayout();
}

void LLMChatPane::grow(void* data)
{
  static_cast<LLMChatPane*>(data)->m_relayout();
}

bool LLMChatPane::setChatFontSize(string s)
{
  s = stripBlankEnds(s);
  if(!isNumber(s))
    return(false);
  int n = atoi(s.c_str());
  if((n < 8) || (n > 32))
    return(false);
  m_chat_font_size = n;
  applyChatFontSize();
  return(true);
}

void LLMChatPane::adjustChatFontSize(int delta)
{
  int n = m_chat_font_size + delta;
  if(n < 8)
    n = 8;
  if(n > 32)
    n = 32;
  if(n == m_chat_font_size)
    return;
  m_chat_font_size = n;
  applyChatFontSize();
}

void LLMChatPane::applyChatFontSize()
{
  m_chat_disp->textsize(m_chat_font_size);
  for(unsigned int i=0; i<6; i++)
    m_chat_styles[i].size = m_chat_font_size;
  m_chat_disp->highlight_data(m_chat_style, m_chat_styles, 6, 'A', 0, 0);

  // Fl_Text_Display recounts its wrapped lines only when its width
  // changes; textsize() just stores the size. With the old total the
  // scrollbar and the scroll clamp stop short and the end of the
  // transcript is out of reach. Re-applying the wrap mode makes FLTK
  // count every line again at the new size (Fl_Text_Display::wrap_mode).
  m_chat_disp->wrap_mode(Fl_Text_Display::WRAP_AT_BOUNDS, 0);

  m_chat_input->textsize(m_chat_font_size);
  m_chat_status->textsize((m_chat_font_size > 9) ? (m_chat_font_size - 1) : m_chat_font_size);
  m_relayout();

  // Fewer lines fit at a larger size: keep the latest line in view
  m_chat_disp->insert_position(m_chat_buff->length());
  m_chat_disp->show_insert_position();
}

static size_t closingQuestionStart(const string& line, size_t qend,
				   size_t floor)
{
  if((qend >= line.size()) || (line[qend] != '?') || (qend <= floor))
    return(qend);
  size_t start = floor;
  for(size_t i = qend; i > floor; i--) {
    size_t j = i - 1;                     // the character before i
    char c = line[j];
    if(c == '\n') {
      start = i;
      break;
    }
    bool ender = (c == '.') || (c == '!') || (c == '?');
    if(ender && (i < qend) && ((line[i] == ' ') || (line[i] == '\t'))) {
      start = i;
      break;
    }
  }
  while((start < qend) && ((line[start] == ' ') || (line[start] == '\t')))
    start++;
  return(start);
}

//----------------------------------------------------------
// Procedure: addChatLine
//   Purpose: Append one line to the transcript and keep the end
//            in view. Newlines arrive encoded as "!@#" so the
//            text survives the MOOSDB and the alog intact.

void LLMChatPane::addChatLine(string who, string text, string mode)
{
  text = findReplace(text, "!@#", "\n");
  string line = who + "> " + text + "\n";

  // The color says what the line is, the prefix says who wrote it
  // (mode "you": another app's line in the operator's color; mode
  // "plan": an event line in the plan color; mode "note": a line that
  // asks nothing of the operator, muted)
  char style = 'B';                       // the model
  if((who == "you") || (mode == "you"))
    style = 'A';
  else if(mode == "ask")
    style = 'C';                          // waiting on the operator
  else if((who == "plan") || (mode == "plan"))
    style = 'D';
  else if(mode == "note")
    style = 'F';                          // asks nothing of the operator

  // A WARNING line inside a proposal (the field check) gets its own
  // color, line by line, so it stands out of the amber block
  string styles(line.size(), style);
  if(mode == "ask") {
    size_t start = 0;
    while(start < line.size()) {
      size_t end = line.find('\n', start);
      if(end == string::npos)
	end = line.size();
      size_t first = line.find_first_not_of(" \t", start);
      if((first != string::npos) && (first < end) && (line.compare(first, 7, "WARNING") == 0))
	styles.replace(start, end - start, end - start, 'E');
      start = end + 1;
    }
  }

  // A reply that ends in a question reads as a reply, its closing
  // question in the ask color; a reply that is all one question is
  // in the ask color whole, its prefix too (2026-11-02)
  if(mode == "question") {
    size_t qend  = line.find_last_of('?');
    size_t floor = who.size() + 2;        // past "who> "
    if((qend != string::npos) && (qend >= floor)) {
      size_t qstart = closingQuestionStart(line, qend, floor);
      if(qstart == floor)
	qstart = 0;
      styles.replace(qstart, qend + 1 - qstart, qend + 1 - qstart, 'C');
    }
  }

  m_chat_buff->append(line.c_str());
  m_chat_style->append(styles.c_str());

  // Keep the transcript bounded, both buffers alike
  if(m_chat_buff->length() > 200000) {
    m_chat_buff->remove(0, 50000);
    m_chat_style->remove(0, 50000);
  }

  m_chat_disp->insert_position(m_chat_buff->length());
  m_chat_disp->show_insert_position();
}

//----------------------------------------------------------
// Procedure: setChatColor
//   Purpose: Config hook: chat_color_<role> = auto | <color name>

bool LLMChatPane::setChatColor(string role, string color)
{
  int idx = -1;
  role = tolower(stripBlankEnds(role));
  if(role == "you")
    idx = 0;
  else if(role == "llm")
    idx = 1;
  else if(role == "ask")
    idx = 2;
  else if(role == "plan")
    idx = 3;
  else if(role == "warn")
    idx = 4;
  else if(role == "note")
    idx = 5;
  if(idx < 0)
    return(false);

  color = tolower(stripBlankEnds(color));
  if((color != "auto") && !isColor(color))
    return(false);
  m_chat_colors[idx] = color;
  return(true);
}

//----------------------------------------------------------
// Procedure: applyChatColors
//   Purpose: Resolve the four role colors against the pane's
//            background. "auto" picks a palette that reads on
//            the light schemes (white, beige) or the dark ones
//            (the indigos); the model's lines use the scheme's
//            own text color so they match the app-casts.

void LLMChatPane::applyChatColors(Fl_Color back, Fl_Color text)
{
  unsigned char r, g, b;
  Fl::get_color(back, r, g, b);
  bool dark = ((0.299 * r + 0.587 * g + 0.114 * b) < 128);

  Fl_Color dflt[6];
  if(dark) {
    dflt[0] = fl_rgb_color(170, 215, 255);   // you: light blue
    dflt[1] = text;                          // llm
    dflt[2] = fl_rgb_color(255, 205, 120);   // ask: amber
    dflt[3] = fl_rgb_color(165, 240, 165);   // plan: pale green
    dflt[4] = fl_rgb_color(255, 110, 110);   // warn: light red
    dflt[5] = fl_rgb_color(150, 150, 150);   // note: grey
  }
  else {
    dflt[0] = fl_rgb_color(0, 60, 180);      // you: blue
    dflt[1] = text;                          // llm
    dflt[2] = fl_rgb_color(180, 70, 0);      // ask: dark orange
    dflt[3] = fl_rgb_color(0, 115, 45);      // plan: green
    dflt[4] = fl_rgb_color(200, 0, 0);       // warn: red
    dflt[5] = fl_rgb_color(115, 115, 115);   // note: grey
  }

  for(int i=0; i<6; i++) {
    Fl_Color c = dflt[i];
    if(m_chat_colors[i] != "auto") {
      ColorPack cpack(m_chat_colors[i]);
      c = fl_rgb_color((int)(cpack.red() * 255), (int)(cpack.grn() * 255),
		       (int)(cpack.blu() * 255));
    }
    m_chat_styles[i].color = c;
  }
  m_chat_disp->redraw();
}

//----------------------------------------------------------
// Procedure: setChatStatus

void LLMChatPane::setChatStatus(string status)
{
  m_chat_status_text = status;
  m_chat_thinking    = strBegins(status, "thinking");
  renderChatStatus();
}

//----------------------------------------------------------
// Procedure: setChatMode / renderChatStatus
//   Purpose: The agent's mode (pLLMAgent posts it on LLM_MODE) beside
//            its status. Planning mode, where the agent asks before
//            it proposes, tints the line amber so it is seen from
//            across the room; review mode, where it reads the run's
//            history and answers why, tints it blue; execution mode
//            leaves the pane's colors.

void LLMChatPane::setChatMode(string mode)
{
  m_chat_mode = tolower(stripBlankEnds(mode));
  if(m_chat_mode == "mission")       // the old word for execution
    m_chat_mode = "execution";
  renderChatStatus();
}

void LLMChatPane::renderChatStatus()
{
  bool planning = (m_chat_mode == "planning");
  bool review   = (m_chat_mode == "review");
  string mode   = (m_chat_mode == "") ? "execution" : m_chat_mode;
  string s = "llm: " + m_chat_status_text + " | " + mode;
  if(m_chat_hint != "")
    s = m_chat_hint;
  m_chat_status->value(s.c_str());
  if(planning || review) {
    m_chat_status->color(planning ? fl_rgb_color(255, 214, 120) : fl_rgb_color(168, 214, 255));
    m_chat_status->textcolor(FL_BLACK);
  }
  else {
    m_chat_status->color(m_chat_status_back);
    m_chat_status->textcolor(m_chat_status_fore);
  }
  m_chat_status->redraw();
}

//----------------------------------------------------------
// Procedure: setChatViewable

bool LLMChatPane::setChatViewable(string str)
{
  if(tolower(str) == "toggle") {
    m_chat_viewable = !m_chat_viewable;
    return(true);
  }
  return(setBooleanOnString(m_chat_viewable, str));
}

//----------------------------------------------------------
// Procedure: setChatWidth
//   Purpose: Percent of the window width, clipped to [15,60].

bool LLMChatPane::setChatWidth(string str)
{
  double pct = 0;
  if(!setDoubleOnString(pct, str))
    return(false);
  if(pct < 15)
    pct = 15;
  if(pct > 60)
    pct = 60;
  m_chat_width = pct / 100.0;
  return(true);
}

//----------------------------------------------------------
// Procedure: setChatInputLines
//   Purpose: How many lines the input grows to before it scrolls.

bool LLMChatPane::setChatInputLines(string str)
{
  int lines = 0;
  if(!setIntOnString(lines, str))
    return(false);
  if(lines < 1)
    lines = 1;
  if(lines > 20)
    lines = 20;
  m_chat_input->setMaxLines(lines);
  return(true);
}
