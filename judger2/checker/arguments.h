#include <iostream>

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
