cmake_minimum_required(VERSION 3.16)
project(Checker)
include(CTest)
include(CheckIPOSupported)

check_ipo_supported(RESULT supported OUTPUT error)

set(CMAKE_CXX_STANDARD 20)

set(CMAKE_CXX_FLAGS "-O2")

add_executable(acmoj-checker
        main.cpp
        check.h
        check.cpp
        arguments.h
        arguments.cpp
)

if (supported)
    message(STATUS "IPO / LTO enabled")
    set_property(TARGET acmoj-checker PROPERTY INTERPROCEDURAL_OPTIMIZATION TRUE)
else ()
    message(STATUS "IPO / LTO not supported: <${error}>")
endif ()

install(TARGETS acmoj-checker DESTINATION bin)
