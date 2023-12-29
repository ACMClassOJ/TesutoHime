cmake_minimum_required(VERSION 3.16)
project(Checker)
include(CTest)
include(CheckIPOSupported)

check_ipo_supported(RESULT supported OUTPUT error)

set(CMAKE_CXX_STANDARD 17)

set(CMAKE_CXX_FLAGS "-O2")

add_executable(checker
    checker.cpp
)

if (supported)
    message(STATUS "IPO / LTO enabled")
    set_property(TARGET checker PROPERTY INTERPROCEDURAL_OPTIMIZATION TRUE)
else ()
    message(STATUS "IPO / LTO not supported: <${error}>")
endif ()
