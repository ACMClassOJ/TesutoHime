/**
 * @file main.cpp
 * @brief Implement an efficient checker with the same behaviour as the `diff -qZB`.
 *
 * The checker process line by line.
 * When the checker reads a line, it will
 * 1. check whether the line is blank. If it is, then skip it.
 * 2. check the line until the last non-blank character.
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

bool SameLine(const std::string& line1, const std::string& line2);
bool BlankLine(const std::string& line);
bool NextNonBlankLine(std::istream& file, std::string& line);
bool CheckFile(std::istream& file1, std::istream& file2);

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "Missing arguments." << std::endl;
        std::cerr << "Usage: " << argv[0] << " <file1> <file2>" << std::endl;
        return 2;
    }

    std::ifstream file1(argv[1]);
    std::ifstream file2(argv[2]);
    if (!file1.is_open() && !file2.is_open()) {
        std::cerr << "Failed to open file: " << argv[1] << std::endl;
        std::cerr << "Failed to open file: " << argv[2] << std::endl;
        return 2;
    }
    if (!file1.is_open()) {
        std::cerr << "Failed to open file: " << argv[1] << std::endl;
        return 2;
    }
    if (!file2.is_open()) {
        std::cerr << "Failed to open file: " << argv[2] << std::endl;
        return 2;
    }

    return CheckFile(file1, file2) ? 0 : 1;
}
