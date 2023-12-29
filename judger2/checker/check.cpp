#include <cctype>
#include <iostream>
#include <string>

bool SameLine(const std::string& line1, const std::string& line2,
              bool ignoreTailingSpace);
bool ReadNextLine(std::istream& file, std::string& line, bool ignoreBlankLine);

/**
 * Check whether two files are the same.
 * The two file must be valid.
 */
bool CheckFile(std::istream& file1, std::istream& file2,
               bool ignoreTailingSpace, bool ignoreBlankLine) {
    std::string line1, line2;
    bool result1 = ReadNextLine(file1, line1, ignoreBlankLine);
    bool result2 = ReadNextLine(file2, line2, ignoreBlankLine);
    while (result1 && result2) {
        if (!SameLine(line1, line2, ignoreTailingSpace)) {
            return false;
        }
        result1 = ReadNextLine(file1, line1, ignoreBlankLine);
        result2 = ReadNextLine(file2, line2, ignoreBlankLine);
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

bool SameLine(const std::string& line1, const std::string& line2,
              bool ignoreTailingSpace) {
    if (!ignoreTailingSpace && line1.size() != line2.size()) {
        return false;
    }
    size_t pos = 0;
    while (pos < line1.size() && pos < line2.size() &&
           line1[pos] == line2[pos]) {
        pos++;
    }
    if (ignoreTailingSpace) {
        return BlankFrom(line1, pos) && BlankFrom(line2, pos);
    } else {
        // no need to check line2 since they must be of the same size
        return pos == line1.size();
    }
}

bool ReadNextLine(std::istream& file, std::string& line, bool ignoreBlankLine) {
    if (!ignoreBlankLine) {
        return static_cast<bool>(std::getline(file, line));
    }
    while (std::getline(file, line)) {
        if (!BlankLine(line)) return true;
    }
    return false;
}
