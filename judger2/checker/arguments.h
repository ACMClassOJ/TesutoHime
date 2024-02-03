#include <iostream>

#ifndef TESUTO_HIME_JUDGER_CHECKER_ARGUMENTS_H_
#define TESUTO_HIME_JUDGER_CHECKER_ARGUMENTS_H_

struct Argument {
    bool valid = false;
    bool isHelp = false;
    bool ignoreTailingSpace = false;
    bool ignoreBlankLine = false;
    bool stdinUsed = false;
    std::istream* file1 = nullptr;
    std::istream* file2 = nullptr;
};

Argument ParseArgument(int argc, char** argv);

#endif //TESUTO_HIME_JUDGER_CHECKER_ARGUMENTS_H_
