#--------------------------------------------------------
# The CMakeLists.txt for:              lib_behaviors-turn
#                                      (BHV_TurnInPlace)
# Author(s):                            West Point RRC
#--------------------------------------------------------

if (${WIN32})
  SET(SYSTEM_LIBS )
else (${WIN32})
  SET(SYSTEM_LIBS m )
endif (${WIN32})

#--------------------------------------------------------
#                                        BHV_TurnInPlace
#--------------------------------------------------------
ADD_LIBRARY(BHV_TurnInPlace SHARED
   BHV_TurnInPlace.cpp)
TARGET_LINK_LIBRARIES(BHV_TurnInPlace
   helmivp
   behaviors
   ivpbuild
   logic
   ivpcore
   bhvutil
   mbutil
   geometry
   ${SYSTEM_LIBS} )
