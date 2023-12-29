#include "arguments.h"

#include <fstream>
#include <iostream>
#include <string>

bool AddFile(Argument& args, std::istream* file);
bool SetAsHelp(Argument& args);
bool ValidHelp(const Argument& args);
bool AddFileByName(Argument& args, const std::string& name);

Argument ParseArgument(int argc, char** argv) {
    Argument args;
    bool allFilesThen = false;
    for (int i = 1; i < argc; ++i) {
        std::string arg(argv[i]);
        if (allFilesThen) {
            if (!AddFileByName(args, arg)) {
                return args;
            }
        } else if (arg.starts_with("--")) {
            std::string remain = arg.substr(2);
            if (remain.empty()) {
                if (ValidHelp(args)) {
                    args.valid = false;
                    return args;
                }
                allFilesThen = true;
            } else if (remain == "ignore-tailing-space") {
                args.ignoreTailingSpace = true;
            } else if (remain == "ignore-blank-lines") {
                args.ignoreBlankLine = true;
            } else if (remain == "help") {
                if (!SetAsHelp(args)) {
                    return args;
                }
            } else {
                std::cerr << "Unknown option: " << arg << std::endl;
                args.valid = false;
                return args;
            }
        } else if (arg.starts_with('-')) {
            std::string remain = arg.substr(1);
            if (remain.empty()) { // "-" for stdin
                if (args.stdinUsed) {
                    std::cerr << "Cannot read from stdin twice" << std::endl;
                    args.valid = false;
                    return args;
                }
                if (AddFile(args, &std::cin)) {
                    continue;
                } else {
                    return args;
                }
            } else {
                for (char c : remain) {
                    switch (c) {
                        case 'Z':
                            args.ignoreTailingSpace = true;
                            break;
                        case 'B':
                            args.ignoreBlankLine = true;
                            break;
                        case 'h':
                            if (!SetAsHelp(args)) {
                                return args;
                            }
                            break;
                        default:
                            std::cerr << "Unknown option: -" << c << std::endl;
                            args.valid = false;
                            return args;
                    }
                }
            }
        } else { // files
            if (!AddFileByName(args, arg)) {
                return args;
            }
        }
    }
    return args;
}

/**
 * Add a file to the argument.
 * @param args
 * @param file
 * @return whether the number of files after adding is valid
 */
bool AddFile(Argument& args, std::istream* file) {
    if (args.isHelp) {
        args.valid = false;
        return false;
    }
    if (args.file1 == nullptr) {
        args.file1 = file;
        return true;
    } else if (args.file2 == nullptr) {
        args.file2 = file;
        args.valid = true;
        return true;
    } else {
        args.valid = false;
        return false;
    }
}

/**
 * Add a file to the argument by its name.
 * @param args
 * @param name
 * @return whether the argument is valid till now
 */
bool AddFileByName(Argument& args, const std::string& name) {
    auto* file = new std::ifstream(name);
    if (!file->is_open()) {
        std::cerr << "Failed to open file: " << name << std::endl;
        delete file;
        return false;
    }
    if (!AddFile(args, file)) {
        delete file;
        return false;
    }
    return true;
}

/**
 * Set the argument as help menu.
 * @param args
 * @return whether the arguments are valid till now
 */
bool SetAsHelp(Argument& args) {
    if (args.file1 != nullptr || args.file2 != nullptr ||
        args.ignoreTailingSpace || args.ignoreBlankLine) {
        args.valid = false;
        return false;
    }
    args.isHelp = true;
    return true;
}

bool ValidHelp(const Argument& args) {
    return args.isHelp && args.file1 == nullptr && args.file2 == nullptr &&
           !args.ignoreTailingSpace && !args.ignoreBlankLine;
}
