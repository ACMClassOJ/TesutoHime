#include <iostream>
#include <string>

bool NextNonBlankLine(std::istream& file, std::string& line);
bool SameLine(const std::string& line1, const std::string& line2);

/**
 * Check whether two files are the same.
 * The two file must be valid.
 */
bool CheckFile(std::istream& file1, std::istream& file2) {
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
    }
    return BlankFrom(line1, pos) && BlankFrom(line2, pos);
}

/**
 * Read the next non-blank line from the file.
 * @param fin The file stream
 * @param line The string to store the line
 * @return Whether the line is read successfully
 */
bool NextNonBlankLine(std::istream& file, std::string& line) {
    while (std::getline(file, line)) {
        if (!BlankLine(line)) return true;
    }
    return false;
}
