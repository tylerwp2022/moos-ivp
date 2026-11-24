# Added by Timeo Williams on 2026-11-24.
IVP_ADD_LIBRARY(llmchat LLMChatPane.cpp LLMChatMail.cpp)
TARGET_LINK_LIBRARIES(llmchat
  PUBLIC "$<BUILD_INTERFACE:ivp_fltk>$<INSTALL_INTERFACE:IVP::FLTK>"
  PRIVATE mbutil ${MOOS_LIBRARIES})
