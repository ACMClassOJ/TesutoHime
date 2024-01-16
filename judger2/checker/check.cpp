#include <cctype>
#include <cstring>
#include <iostream>
#include <string>

constexpr size_t kBufferSize = 4096;

bool CompareFileDirectly(std::istream& file1, std::istream& file2);
bool SameLine(const std::string& line1, const std::string& line2,
              bool ignoreTailingSpace);
bool ReadNextLine(std::istream& file, std::string& line, bool ignoreBlankLine);

/**
 * Check whether two files are the same.
 * The two file must be valid.
 */
bool CheckFile(std::istream& file1, std::istream& file2,
               bool ignoreTailingSpace, bool ignoreBlankLine) {
    if (!ignoreTailingSpace && !ignoreBlankLine) {
        return CompareFileDirectly(file1, file2);
    }
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

/**
 * Compare two files directly.
 * This function compares two files by reading them into a buffer of
 * <code>kBufferSize</code>. To avoid using too much memory, the buffer
 * size cannot be large. To improve the performance (maybe with the help of
 * SIMD), the buffer size should not be small.
 * @param file1
 * @param file2
 */
bool CompareFileDirectly(std::istream& file1, std::istream& file2) {
    struct Buffer {
        Buffer() { buffer = new char[kBufferSize]; }
        ~Buffer() { delete[] buffer; }
        char* buffer;
    };
    Buffer buffer1, buffer2;
    while (static_cast<bool>(file1) && static_cast<bool>(file2)) {
        file1.read(buffer1.buffer, kBufferSize);
        file2.read(buffer2.buffer, kBufferSize);
        auto size1 = file1.gcount();
        auto size2 = file2.gcount();
        if (size1 != size2 ||
            std::memcmp(buffer1.buffer, buffer2.buffer, size1) != 0) {
            return false;
        }
    }
    return !static_cast<bool>(file1) && !static_cast<bool>(file2);
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
