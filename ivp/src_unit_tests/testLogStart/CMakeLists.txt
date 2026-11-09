# Regression checks for timestamp headers consumed by log readers.
ADD_EXECUTABLE(testLogStart main.cpp)
TARGET_INCLUDE_DIRECTORIES(testLogStart PRIVATE ../../src/lib_logutils)
TARGET_LINK_LIBRARIES(testLogStart logutils mbutil)
