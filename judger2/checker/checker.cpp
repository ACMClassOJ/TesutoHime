/**
 * @file checker.cpp
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
bool NextNonBlankLine(std::ifstream& file, std::string& line);
bool CheckFile(std::ifstream& file1, std::ifstream& file2);

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

/**
 * Check whether two files are the same.
 * The two file must be valid.
 */
bool CheckFile(std::ifstream& file1, std::ifstream& file2) {
    std::string line1, line2;
    bool result1 = NextNonBlankLine(file1, line1);
    bool result2 = NextNonBlankLine(file2, line2);
    while (result1 && result2) {
        if (!SameLine(line1, line2)) {
            return false;
        }
        result1 = NextNonBlankLine(file1, line1);
        result2 = NextNonBlankLine(file2, line2);
    }
    return result1 == result2;
}

bool BlankFrom(const std::string& line, size_t pos) {
    for (size_t i = pos; i < line.size(); i++) {
        if (!std::isspace(line[i])) {
            return false;
        }
    }
    return true;
}

bool BlankLine(const std::string& line) {
    return BlankFrom(line, 0);
}

bool SameLine(const std::string& line1, const std::string& line2) {
    // Note: the line cannot be blank, so the prefix must be the same.
    size_t pos = 0;
    while (pos < line1.size() && pos < line2.size() &&
           line1[pos] == line2[pos]) {
        pos++;
        pos++;
    }
    if (pos == line1.size() && pos == line2.size()) {
        return true;
    } else if (pos == line1.size()) {
        // line2 doesn't reach the end.
        return BlankFrom(line2, pos);
    } else if (pos == line2.size()) {
        // line1 doesn't reach the end.
        return BlankFrom(line1, pos);
    } else {
        // Both line1 and line2 don't reach the end.
        return BlankFrom(line1, pos) && BlankFrom(line2, pos);
    }
}

/**
 * Read the next non-blank line from the file.
 * @param fin The file stream
 * @param line The string to store the line
 * @return Whether the line is read successfully
 */
bool NextNonBlankLine(std::ifstream& file, std::string& line) {
    while (std::getline(file, line)) {
        if (!BlankLine(line)) return true;
    }
    return false;
}
