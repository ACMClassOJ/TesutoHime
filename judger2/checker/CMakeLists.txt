cmake_minimum_required(VERSION 3.16)
project(Checker)
include(CTest)

set(CMAKE_CXX_STANDARD 17)

set(CMAKE_CXX_FLAGS "-O2")

add_executable(checker
    checker.cpp
)
