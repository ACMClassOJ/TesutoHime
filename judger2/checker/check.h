#include <iostream>

#ifndef TESUTO_HIME_JUDGER_CHECKER_CHECK_H_
#define TESUTO_HIME_JUDGER_CHECKER_CHECK_H_

bool CheckFile(std::istream& file1, std::istream& file2,
               bool ignoreTailingSpace, bool ignoreBlankLine);

#endif //TESUTO_HIME_JUDGER_CHECKER_CHECK_H_
