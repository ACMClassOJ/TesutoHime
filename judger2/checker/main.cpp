/**
 * @file main.cpp
 *
 * Exit code:
 * 0: No difference;
 * 1: Different;
 * 2: Missing arguments.
 */

#include <cctype>
#include <fstream>
#include <iostream>
#include <string>

#include "arguments.h"
#include "check.h"

void PrintHelpMenu();

int main(int argc, char** argv) {
    Argument args = ParseArgument(argc, argv);
    if (!args.valid) {
        PrintHelpMenu();
        return 2;
    }
    if (args.isHelp) {
        PrintHelpMenu();
        return 0;
    }
    return CheckFile(*args.file1, *args.file2,
                     args.ignoreTailingSpace, args.ignoreBlankLine) ? 0 : 1;
}

void PrintHelpMenu() {
    std::cout << R"(Usage: checker [OPTION]... FILE1 FILE2
Compare two files line by line.

Options:
  -Z, --ignore-tailing-space  ignore the white space at the end of the line
  -B, --ignore-blank-lines    ignore the blank lines
  -h, --help                  display this help and exit
  -                           read from stdin
  --                          end of options

Exit status:
    0  if no difference
    1  if difference
    2  if missing arguments
)" << std::endl;
}
