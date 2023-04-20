# 数据格式规范

by cong258258，Anoxiacxy，Alan-Liang，LauYeeYu，更新于 2023.2.16

## ZIP总格式

- **数据包名称**：`题号.zip`（如 `1000.zip`），**请确认题号与题面中的 id（即数据库主键）保持一致再上传传输数据包**。
- **数据包目录结构**：`题号.zip/题号/所有文件`，如 `1000.zip/1000/1.in`
- **可能包含的内容及大致情况**：
  - （所有题目类型必须）一个 `config.json`，包含所有评测方法的信息。
  - （除特殊情况外，所有题目类型必须）一个 `description.md`，即题面信息。请参考[题面格式规范文档](problem-format-doc)。
  - （强烈建议）`solution.cpp`，即标程。
  - （大部分情况下需要，verilog 评测不支持）若干 `数字.in`，即传统 OI 题中的输入文件。**文件名请采用连续编号的，从1开始的纯数字**，与 `.out` 对应。
  - （大部分情况下需要，部分 spj 不需要）若干 `数字.out`，即传统 OI 题中的正确输出。**文件名请采用连续编号的，从1开始的纯数字**，与 `.in` 对应。
  - （评测 .h 头文件需要）若干 `数字.cpp`，他们将引用学生上传的头文件（评测时保存在 `src.hpp`）进行评测。**文件名请采用连续编号的，从1开始的纯数字**。你需要 `#include "src.hpp"`。
  - （spj 需要）一个 `spj.cpp`，传入参数见详情。
  - （可选）任意题目可能需要的文件，如：插图（**请确保插图上传到 OJ 自带图床，能从互联网访问后引用 URL 而不是直接本地引用**），数据生成脚本，`config.json` 生成脚本，数据随机种子，辅助网页等信息。
- [数据包样例](package-sample)中提供了一些常见的数据包结构，可供参考。但请注意，请**务必先认真阅读本文档**，数据包样例不能涵盖全部信息。

### CPP 评测
除上述要求外，还需包含 `.h` 或 `.hpp`，如果在评测时（如评测头文件，评测 spj）需要引入其他头文件。同时将文件名填入 `config.json` 的 `SupportedFiles`，参见 [SupportedFiles 章节](#supportedfiles)。

### Verilog 评测
若干 `数字.v`，他们将引用学生上传的 `.v` 模块（评测时保存在 `answer.v`）进行评测。**文件名请采用连续编号的，从 1 开始的纯数字**。你需要 <code>`include "answer.v"</code>。

## config.json

### Groups

- GroupID：连续编号，从 1 开始的纯数字。
- GroupName：若不存在可填`""`。
- GroupScore：该评测组的满分。
- TestPoints：一个数组，数组元素为本组包含的一个/多个测试点在 Details 列表中的次序。将这些测试点的得分**取最小值**，乘以上述 GroupScore（该评测组的满分），即得到该测试组的最终得分。（一般情况下，我们要求 SPJ 给出的测试点得分为一个 0 ~ 1 之间的小数；对于非 SPJ 的情况，通过此测试点为 1 ，否则为 0）。作为**取最小值**这一行为的一个特例，非 SPJ 给分的测试组需要其下所有测试点 AC ，才能得到该评测组的分数。**即使本组只有一个测试点，TestPoints 也必须是一个数组！**

### Details
- ID：这个ID和数据包下的文件名对应，`1` 对应 1.in / 1.out / 1.ans / 1.cpp。
- Dependency：依赖测试点，如果某个测试点需要在其他测试点通过后再进行测试，可以填写其他测试点的编号，无依赖性的时候填写 `0`。注意，这里的编号不是上述的ID，而是测试点在 Details 列表中的次序。当然，如果你的 ID 编号从 1 开始且连续递增，那么 ID 和 Details 列表中的次序是一样的。
- TimeLimit：建议值 1000（1秒），单位 ms。
- MemoryLimit：建议值 268435456（256MB），单位 byte。
- DiskLimit：如果不使用，建议值 0，单位 byte。负数表示新开空间，正数不会新开空间，仅作为 Disk Limit Exceed 的参考标准。如，测试组 1 的 Details 包含测试点 1, 2, 3（三个点顺序依赖），通过将他们的 DiskLimit 分别设置为 -512000000, 512000000, 512000000，就可以实现这三个点共享约 512MB 的测试磁盘空间，且在 1, 2 运行结束时留下的文件不会被删除，仍可被接下来运行的测试点读取；仅在测试点 3 运行结束后销毁所有文件。
- FileNumberLimit：文件数量限制。
- ValgrindTestOn：True / False，是否开启精细化的内存泄漏检测。请注意，Valgrind 会**大大降低评测速度**，程序运行时间将延长 10-100 倍，因此需要**扩大时间限制**。另外，建议加入**不带内存泄漏检查**的测试点，并作为该测试点的依赖 (Dependency)，以减少错误提交的测试时间。
  
### CompileTimeLimit
建议值 10000（10秒），单位 ms，如需从 Git 拉取编译评测可适当增加。

### SPJ
- spj 0 single file with diff
  - 这是通常类型题目将会使用到的评测类型，将会直接编译用户提交的代码，使用 `*.in` 作为程序输入，`*.out/ans` 作为标准答案，直接和程序输出进行 `diff` 比较来给分。

- spj 1 single file with spj
  - 这是答案不唯一的题目可能会使用到的评测类型，流程和 spj 0 基本相同，只是在获取了程序输出之后，会将程序输出，`*.in` 和 `*.out/ans` 文件交付给出题人自定义的 `spj_bin` 或 `spj.cpp` 文件进行评测，具体参见 [SPJ File 部分](#spj-file)。

- spj 2 hpp without diff
  - 这是需要对头文件进行测试的评测类型，用户提交的代码将会被保存在 `src.hpp` 中。在数据包的根目录下需要有 `main.cpp` 或者 `1.cpp`、`2.cpp` 这样的文件，文件中需要 `#include "src.hpp"`，即可调用用户提交的代码进行测试。程序输出的就是最终的得分，所以你需要有一些奇特的方法来避免用户在 `src.hpp` 中输出一些奇怪的内容而影响最终的评分。更好的评测方式应该是使用 spj 4。注意，该评测类型可能不需要使用到 `*.out/ans` 文件。

- spj 3 hpp with diff
  - 这同样是对头文件进行测试的评测类型，但是在最终的评分环节，是将输出和 `*.out/ans` 进行 `diff` 比对而给分的。

- spj 4 hpp with spj
  - 这是一个 spj 2/3 的完美替代品，用户提交的代码会被保存在 `src.hpp` 里面，数据包内需要包含 `main.cpp` 或者 `1.cpp`、`2.cpp`，这些文件将会被一起编译成用户程序 `program`，数据包还需要有另外的 `spj_bin` 或 `spj.cpp`，它接受 `program` 程序的输出，`*.in` 、`*.out/ans` 作为参数，具体参见 [SPJ File 部分](#spj-file)。一个解决 spj 2 中用户输出或者输入的方法是将文件 `*.in` 加密，并加入完整性检测的 MD5，以防止用户程序擅自在 `src.hpp` 中读入，可以在 `program` 的输出也加入完整性检测的 MD5，同时使用 `spj_bin` 或 `spj.cpp` 对 `program` 的输出进行检测，以防止用户程序擅自在 `src.hpp` 中输出。

- spj 5 output only
  - 这里将直接把用户提交的文件作为 `userOutput` 传递给 `spj_bin` 或 `spj.cpp`，如果你的 `spj_bin` 或 `spj.cpp` 中内置了一个编译器，理论上你可以支持所有程序语言的评测。关于 `spj_bin` 或 `spj.cpp`，具体参见 [SPJ File 部分](#spj-file)。

### SupportedFiles
一个数组，包含运行时需要额外引用的非库的头文件。**注意**，这里引入的文件需要被放入数据包的根目录下，而且该文件只会在文件的编译期被使用，程序运行时是不可以使用到这里的文件的。例：

```json
  "SupportedFiles": [
        "utility.hpp",
        "exceptions.hpp",
        "class-bint.hpp",
        "class-integer.hpp",
        "class-matrix.hpp"
    ]
```

### Verilog
是否启用 Verilog 评测，启用为 `true`，否则为 `false` 。默认为 `false`。请注意，如果启用该选项，所有的提交的将会**强制**被视作 Verilog。关于 Verilog 评测的更多信息，请参阅 [Verilog 评测章节](#verilog-评测)。

### Quiz
是否是填选题，填选题为 `true`，否则为 `false`。默认为 `false`。

## description.md
- 题面信息请参考[题面格式规范文档](problem-format-doc)。
- 在数据包中放 `description.md` 仅仅是为了数据包的完整性给以后的助教和管理员提供便利，其本身与数据库和网页题面显示并没有关联。
- 因此重新上传数据包，`description.md` 中的改动并不会体现在网页上；
- 通过网页或其他方式修改题面后，改动也不会同步到数据包里，请知悉；
- 若 Markdown 格式不方便，也可以使用 txt/word 等文本格式。
- 若无必要给出题面情况（比如大作业的题面在 GitHub 上），这一项可不放。
- 若需要插入图片，建议上传到 ACM OJ 图床服务，建议使用 `<img>` 标签插入题面以更好的控制题目格式。
- 建议将时空限制在数据范围中注明。

## solution.cpp
- 在数据包中放标程仅仅是为了数据包的完整性给以后的助教和管理员提供便利，其本身与评测并没有关联。
- 若存在难以给出标程情况（比如大作业），这一项可不放。
- 也欢迎放上部分分解法，命名可以是 `solution60.cpp`，`solution_n2.cpp` 等。
- 对于所有评测 cpp 类题目，避免将标答命名为 `main.cpp`。
- 对于评测头文件类题目，避免将标答命名为 `src.h`、`src.hpp`。
- 对于评测 verilog 类题目，避免将标答命名为 `answer.v`。
- 对于存在从 stdin 读取信息的评测，不需要 freopen。
- 对于传统的输出 stdout 与各测试点简单比对结果的评测，不需要 freopen。

## 1.in
- 即传统 OI 题中从 stdin 输入的文件。
- 命名规范：若干 `数字.in`，**文件名请采用连续编号的，从1开始的纯数字**，与 `.out/ans` 对应。
- 在评测 `.h` 头文件时，可能不需要从 stdin 读取信息而将测试点嵌在各个 cpp（`1.cpp`）里，此时可不存在 `.in`。
- 在使用 spj.cpp 时，可能不需要从 stdin 读取信息而将测试点嵌在 spj（`spj.cpp`）里，此时可不存在`.in`。
- 在评测 verilog 时，尚不支持任何方式的读取输入，请将测试点内嵌至testbench（`1.v`）。
- 注意：我们的 OJ 评测均采用 Linux 环境，默认 diff 时有行末空格过滤。虽然对于许多题目，换行符为 Windows 的 CRLF(`\r\n`) 还是 Linux 的 LF(`\n`) 并不会产生很大的影响，但请各位出数据的助教尽可能不要出现 CRLF。

## 1.out / 1.ans
- 即传统 OI 题中的正确输出，他们将与程序的 stdout 输出进行比对。
- 命名规范：若干 `数字.out` 或 `数字.ans`，**文件名请采用连续编号的，从1开始的纯数字**，与 `.in` 对应。同时存在 `.out` 和 `.ans` 时后者优先级高。
- 在使用 spj.cpp 时，可能不需要比对 stdout，此时可不存在 `.out`。
- 注意：我们的 OJ 评测均采用 Linux 环境，默认 diff 时有行末空格过滤。虽然对于许多题目，换行符为 Windows 的 CRLF(`\r\n`) 还是 Linux 的 LF(`\n`) 并不会产生很大的影响，但请各位出数据的助教尽可能不要出现 CRLF。

## SPJ File

如果需要编写特定的 spj 程序，如 spj1、spj4、spj5，可以使用 `spj_bin` 或 `spj.cpp`。

当存在 `spj_bin` 时，会优先使用 `spj_bin`。

`spj_bin` 是一个可执行文件（OJ 会自动给予执行权限）；`spj.cpp` 是一个 C++ 源文件，OJ 会将其编译成可执行文件。

### spj_bin

`spj_bin` 通过命令行（argv[]）传参，具体如下：

```sh
./spj input output answer score message
```

其中：

- input 是题目的输入文件
- output 是用户输出
- answer 是题目的答案
- score 是把评测的分数
- message 是错误/提示信息

`spj_bin` 可以是二进制文件，也可以是 shell/python 脚本。

### spj.cpp

`spj.cpp` 通过命令行（argv[]）传参，具体如下：

```cpp
FILE *input   = fopen(argv[1], "r"); // 题目的输入文件
FILE *output  = fopen(argv[2], "r"); // 用户输出
FILE *answer  = fopen(argv[3], "r"); // 题目的答案
FILE *score   = fopen(argv[4], "w"); // 把评测的分数输出到这里
FILE *message = fopen(argv[5], "w"); // 这里输出错误/提示信息
```

score 中只有一个 double 类型的数，如果值为 1，那么该测试点会被判断为 AC，否则为 WA。此功能可以实现部分赋分，例如将一个 groupScore 设为 100，且只包含一个测试点，如果 score 中的 double 数为
0.5，那么该 group 的得分就是 50 分。

message 功能：这部分信息将显示到 OJ 上供选手查看。
