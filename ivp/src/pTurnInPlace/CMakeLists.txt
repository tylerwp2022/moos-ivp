#--------------------------------------------------------
# The CMakeLists.txt for:                    pTurnInPlace
# Author(s):                            West Point RRC
#--------------------------------------------------------

SET(SRC
  TurnInPlace.cpp
  TurnInPlace_Info.cpp
  main.cpp
)

ADD_EXECUTABLE(pTurnInPlace ${SRC})

TARGET_LINK_LIBRARIES(pTurnInPlace
  ${MOOS_LIBRARIES}
  geometry
  apputil
  mbutil
  m
  pthread)
