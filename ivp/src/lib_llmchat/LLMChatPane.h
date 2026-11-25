/*****************************************************************/
/*    NAME: Tyler Errico                                         */
/*    ORGN: West Point Robotics Research Center                  */
/*    FILE: LLMChatPane.h                                      */
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

#ifndef LLM_CHAT_PANE_HEADER
#define LLM_CHAT_PANE_HEADER

#include <functional>
#include <string>
#include <FL/Fl_Menu_Bar.H>
#include <FL/Fl_Output.H>
#include "LLMChatInput.h"
#include "LLMChatSplitter.h"

class LLMChatPane {
 public:
  enum class Post {Message, Interrupt};

  explicit LLMChatPane(std::function<void()> relayout);
  ~LLMChatPane();

  void addMenu(Fl_Menu_Bar&, const std::string& prefix);
  void setPost(std::function<bool(Post, const std::string&)> post) {m_post = post;}
  bool configure(const std::string& param, const std::string& value);
  bool inputHasFocus() const {return Fl::focus() == m_chat_input;}

  // Width reserved at the right edge, including the drag splitter.
  int reservedWidth(int window_width, int available_width, int min_content) const;
  void layout(int window_width, int y, int reserved_width, int height,
              Fl_Color background, Fl_Color foreground);

  void addChatLine(std::string who, std::string text, std::string mode="");
  void setChatStatus(std::string);
  void setChatMode(std::string);
  void setChatCommands(std::string);

 private:
  static void send(Fl_Widget*, void*);
  static bool interrupt(void*);
  static void hint(void*, const std::string&);
  static void clearHint(void*);
  static void grow(void*);
  static void drag(Fl_Widget*, void*);
  static void toggle(Fl_Widget*, void*);
  static void wider(Fl_Widget*, void*);
  static void narrower(Fl_Widget*, void*);
  static void larger(Fl_Widget*, void*);
  static void smaller(Fl_Widget*, void*);

  void sendMessage();
  bool interruptTurn();
  bool setChatViewable(std::string);
  bool setChatWidth(std::string);
  bool setChatInputLines(std::string);
  bool setChatFontSize(std::string);
  bool setChatColor(std::string, std::string);
  void adjustChatWidth(double);
  void adjustChatFontSize(int);
  void applyChatFontSize();
  void applyChatColors(Fl_Color, Fl_Color);
  void renderChatStatus();

  std::function<void()> m_relayout;
  std::function<bool(Post, const std::string&)> m_post;

  Fl_Text_Display *m_chat_disp;
  Fl_Text_Buffer  *m_chat_buff;
  Fl_Text_Buffer  *m_chat_style;      // one style letter per byte of m_chat_buff
  Fl_Text_Display::Style_Table_Entry m_chat_styles[6];  // A you, B llm, C ask, D plan, E warn, F note
  std::string      m_chat_colors[6];  // "auto" or a color name, same order
  LLMChatInput   *m_chat_input;
  Fl_Output       *m_chat_status;
  std::string      m_chat_status_text;  // the agent's status word(s)
  std::string      m_chat_mode;         // execution | planning | review
  std::string      m_chat_hint;         // Tab's candidates or a command's arguments, on the status row for a moment
  Fl_Color         m_chat_status_back;  // the pane's colors, restored in execution mode
  Fl_Color         m_chat_status_fore;
  std::string      m_chat_last_sent;     // the line Enter sent last, back in the box after an interrupt
  bool             m_chat_thinking;      // the status word begins with "thinking"
  bool             m_chat_viewable;
  int              m_chat_font_size;
  double           m_chat_width;    // fraction of window width
  LLMChatSplitter *m_chat_split;

};

#endif
