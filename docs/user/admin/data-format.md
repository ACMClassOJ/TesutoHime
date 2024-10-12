# 数据格式规范

*By cong258258，Anoxiacxy，Alan-Liang，LauYeeYu，更新于 2024.10.11。*

## ZIP总格式

*注：请尽量使用避免任何未在此处出现的特性或问题（特别是做出某个特定文件名的文件存在的假设），因为这可能在评测后端升级后发生变化。*

- **数据包名称**：`题号.zip`（如 `1000.zip`），**请确认题号与题面中的 id（即数据库主键）保持一致再上传传输数据包**。
- **数据包目录结构**：`题号.zip/题号/所有文件`，如 `1000.zip/1000/1.in`
- **可能包含的内容及大致情况**：
  - （所有题目类型必须）一个 `config.json`，包含所有评测方法的信息。
  - （除特殊情况外，所有题目类型必须）一个 `description.md`，即题面信息。请参考[题面格式规范](problem-format.md)。
  - （强烈建议）`solution.cpp`，即标程。
  - （大部分情况下需要，verilog 评测不支持）若干 `数字.in`，即传统 OI 题中的输入文件。**文件名请采用连续编号的，从1开始的纯数字**，与 `.ans` 对应。
  - （大部分情况下需要，部分 spj 不需要）若干 `数字.ans`，即传统 OI 题中的正确输出。**文件名请采用连续编号的，从1开始的纯数字**，与 `.in` 对应。
  - （评测 `.hpp` 头文件需要）若干 `数字.cpp` 或 `main.cpp`，他们将引用学生上传的头文件（评测时保存在 `src.hpp`）进行评测。**文件名请采用连续编号的，从 1 开始的纯数字**。你需要在 C++ 源文件中加上 `#include "src.hpp"`。
  - （自定义 checker 需要）一个 `spj.cpp`，传入参数见详情。
  - （I/O 交互题需要）一个 `interactor.cpp`，传入参数见详情。
  - （可选）任意题目可能需要的文件，如：插图（**请确保插图上传到 OJ 自带图床，能从互联网访问后引用 URL 而不是直接本地引用**），数据生成脚本，`config.json` 生成脚本，数据随机种子，辅助网页等信息。
- [数据包样例](package-sample.md)中提供了一些常见的数据包结构，可供参考。但请注意，请**务必先认真阅读本文档**，数据包样例不能涵盖全部信息。
- **输出文件大小限制：**输出文件大于 256 MiB 时会报错 (File size limit exceeded)，请确保题目的标准答案不会超过 256 MiB。
- **数据包大小限制：**数据包压缩后总大小大于 100 MiB 时无法直接上传，最好不要使用如此大的数据包。如果您确实需要大于 100 MiB 的数据包，请联系 ACM 班服务器管理员提供权限。
  - 不要使用极大的数据来卡常或卡 log。如果数据是均匀随机的，可以用每个测试点的随机数种子作为输入，运行时动态生成数据。

### C++ 评测

如果编译时需要包含任何题目提供的头文件（不包含选手提交的代码），需要将文件名填入 `config.json` 的 `SupportedFiles`，参见 [SupportedFiles 部分](#supportedfiles)。

### Verilog 评测

若干 `数字.v`，他们将引用学生上传的 `.v` 模块（评测时保存在 `answer.v`）进行评测。**文件名请采用连续编号的，从 1 开始的纯数字**。你需要 <code>`include "answer.v"</code>。

## description.md

- 题面信息请参考[题面格式规范](problem-format.md)。
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
- 在使用 spj.cpp 时，可能不需要从 stdin 读取信息而将测试点嵌在 checker（`spj.cpp`）里，此时可不存在`.in`。
- 在评测 verilog 时，尚不支持任何方式的读取输入，请将测试点内嵌至testbench（`1.v`）。
- 注意：我们的 OJ 评测均采用 Linux 环境，默认 diff 时有行末空格过滤。虽然对于许多题目，换行符为 Windows 的 CRLF (`\r\n`) 还是 Linux 的 LF (`\n`) 并不会产生很大的影响，但请各位出数据的助教尽可能不要出现 CRLF。

## 1.ans / 1.out

- 即传统 OI 题中的正确输出，他们将与程序的 stdout 输出进行比对。
- 命名规范：若干 `数字.ans` 或 `数字.out`，**文件名请采用连续编号的，从1开始的纯数字**，与 `.in` 对应。同时存在 `.out` 和 `.ans` 时后者优先级高。
- 在使用 spj.cpp 时，可能不需要比对 stdout，此时可不存在 `.ans`。
- 注意：我们的 OJ 评测均采用 Linux 环境，默认 diff 时有行末空格过滤。虽然对于许多题目，换行符为 Windows 的 CRLF (`\r\n`) 还是 Linux 的 LF (`\n`) 并不会产生很大的影响，但请各位出数据的助教尽可能不要出现 CRLF。

## config.json

如果您使用 VS Code，您可以在 config.json 中加入一行：

```json
{
  "$schema": "https://acm.sjtu.edu.cn/OnlineJudge/static/assets/problem-config.schema.json",
  ...
}
```

以获得更好的代码补全体验。

### Groups

- GroupID：连续编号，从 1 开始的纯数字。
- GroupName：若不存在可填 `""`。
- GroupScore：该评测组的满分。
- TestPoints：一个数组，数组元素为本组包含的一个/多个测试点在 Details 列表中的次序。将这些测试点的得分**取最小值**，乘以上述 GroupScore（该评测组的满分），即得到该测试组的最终得分。（一般情况下，我们要求 SPJ 给出的测试点得分为一个 0 ~ 1 之间的小数；对于非 SPJ 的情况，通过此测试点为 1 ，否则为 0）。作为**取最小值**这一行为的一个特例，非 SPJ 给分的测试组需要其下所有测试点 AC ，才能得到该评测组的分数。**即使本组只有一个测试点，TestPoints 也必须是一个数组！**

### Details

- ID：这个ID和数据包下的文件名对应，`1` 对应 1.in / 1.ans / 1.cpp。
- Dependency：依赖测试点，如果某个测试点需要在其他测试点通过后再进行测试，可以填写其他测试点的编号，无依赖性的时候填写 `0`。注意，这里的编号不是上述的ID，而是测试点在 Details 列表中的次序。当然，如果你的 ID 编号从 1 开始且连续递增，那么 ID 和 Details 列表中的次序是一样的。
- TimeLimit：建议值 1000（1秒），单位 ms。
- MemoryLimit：建议值 268435456（256MB），单位 byte。
- DiskLimit：如果不使用，建议值 0，单位 byte。负数表示新开空间，正数不会新开空间，仅作为 Disk Limit Exceed 的参考标准。如，测试组 1 的 Details 包含测试点 1, 2, 3（三个点顺序依赖），通过将他们的 DiskLimit 分别设置为 -512000000, 512000000, 512000000，就可以实现这三个点共享约 512MB 的测试磁盘空间，且在 1, 2 运行结束时留下的文件不会被删除，仍可被接下来运行的测试点读取；仅在测试点 3 运行结束后销毁所有文件。
- FileNumberLimit：文件数量限制。
- ValgrindTestOn：True / False，是否开启精细化的内存泄漏检测。请注意，Valgrind 会**大大降低评测速度**，程序运行时间将延长 10-100 倍，因此需要**扩大时间限制**。另外，建议加入**不带内存泄漏检查**的测试点，并作为该测试点的依赖 (Dependency)，以减少错误提交的测试时间。

### CompileTimeLimit

建议值 10000（10秒），单位 ms，如需从 Git 拉取编译评测可适当增加。

### SPJ

评测分为三个步骤，每个步骤都可以进行一定程度上的自定义。对于传统题目，可以省略此项。

#### 编译（Compile）

将选手提交的程序编译为可执行文件。支持以下三种类型：

- skip：不编译。
- classic：对于 C++ 或 Verilog 代码，将选手提交的程序作为入口点进行编译；对于 Python 代码，不编译。
- hpp：仅支持提交 C++。在数据包的根目录下需要有 `main.cpp` （所有测试点均使用这个入口点）或者 `1.cpp`、`2.cpp` （每个测试点对应的入口点）这样的文件作为入口点，选手提交的程序将保存在 `src.hpp` 中。出题人应在入口点中 `#include "src.hpp"`，以调用用户提交的代码进行测试。

默认为 classic。

#### 运行（Run）

运行选手提交的程序。对于 I/O 交互题，同时运行交互器。支持以下四种类型：

- skip：不运行，直接将选手提交的代码作为输出交给 checker。
- classic：运行选手程序，从标准输入读入，答案写到标准输出。
- verilog：运行选手提交的 Verilog 程序。（Verilog 程序需要使用 `vvp` 解释器运行。）
- interactive：I/O 交互，同时运行选手程序和另一个题目提供的「交互器」（interactor），具体使用方法参见 [I/O 交互题部分](#io-交互题)。

默认为 classic。

#### 检查（Check）

运行检查器，给出评测结果。支持以下三种类型：

- skip：不检查，直接以运行结果作为评测结果。运行结果的第一行应是一个 0 至 1 之间的数，表示得分占测试点总分的比例，0 为不得分，1 为满分（accepted），其余内容会作为测试点的评测消息展示给选手。
- compare：逐字符对比运行结果和标准答案，相同则满分，不同则不得分。对比时默认忽略行末空白符和空行，相当于 `diff -ZB`。如果希望不忽略，可以将 `IgnoreInsignificantWhitespace` 设为 false。
- custom：自定义 checker，见 [自定义 Checker 部分](#自定义-checker)。

默认为 compare，IgnoreInsignificantWhitespace 为 true。

#### config.json 格式

在 config.json 中，可以指定这三个步骤的类型。例如：

```json
  "SPJ": {
    "Compile": "classic",
    "Run": "classic",
    "Check": "custom"
  }
```

默认值可以省略：

```json
  "SPJ": {
    "Check": "custom"
  }
```

如果该类型有需要填写的参数，则需要这样写出：

```json
  "SPJ": {
    "Check": {
      "Type": "compare",
      "IgnoreInsignificantWhitespace": false
    }
  }
```

几种常用的 SPJ 类型可以直接写为数字：

- spj 0 single file with diff

  这是通常类型题目将会使用到的评测类型，将会直接编译用户提交的代码，使用 `*.in` 作为程序输入，`*.out/ans` 作为标准答案，直接和程序输出进行 `diff` 比较来给分。

  `"SPJ": 0` 相当于：

  ```json
    "SPJ": {
      "Compile": "classic",
      "Run": "classic",
      "Check": "compare",
    }
  ```

- spj 1 single file with spj

  这是答案不唯一的题目可能会使用到的评测类型，流程和 spj 0 基本相同，只是在获取了程序输出之后，会将程序输出，`*.in` 和 `*.out/ans` 文件交付给出题人自定义的 `spj_bin` 或 `spj.cpp` 文件进行评测，具体参见 [自定义 Checker 部分](#自定义-checker)。

  `"SPJ": 1` 相当于：

  ```json
    "SPJ": {
      "Compile": "classic",
      "Run": "classic",
      "Check": "custom",
    }
  ```

- spj 2 hpp without diff

  这是需要对头文件进行测试的评测类型，用户提交的代码将会被保存在 `src.hpp` 中。在数据包的根目录下需要有 `main.cpp` 或者 `1.cpp`、`2.cpp` 这样的文件，文件中需要 `#include "src.hpp"`，即可调用用户提交的代码进行测试。程序输出的就是最终的得分，所以你需要有一些奇特的方法来避免用户在 `src.hpp` 中输出一些奇怪的内容而影响最终的评分。更好的评测方式应该是使用 spj 4。注意，该评测类型可能不需要使用到 `*.out/ans` 文件。

  `"SPJ": 2` 相当于：

  ```json
    "SPJ": {
      "Compile": "hpp",
      "Run": "classic",
      "Check": "skip",
    }
  ```

- spj 3 hpp with diff

  这同样是对头文件进行测试的评测类型，但是在最终的评分环节，是将输出和 `*.out/ans` 进行 `diff` 比对而给分的。

  `"SPJ": 3` 相当于：

  ```json
    "SPJ": {
      "Compile": "hpp",
      "Run": "classic",
      "Check": "compare",
    }
  ```

- spj 4 hpp with spj

  这是一个 spj 2/3 的完美替代品，用户提交的代码会被保存在 `src.hpp` 里面，数据包内需要包含 `main.cpp` 或者 `1.cpp`、`2.cpp`，这些文件将会被一起编译成用户程序 `program`，数据包还需要有另外的 `spj_bin` 或 `spj.cpp`，它接受 `program` 程序的输出，`*.in` 、`*.out/ans` 作为参数，具体参见 [自定义 Checker 部分](#自定义-checker)。一个解决 spj 2 中用户输出或者输入的方法是将文件 `*.in` 加密，并加入完整性检测的 MD5，以防止用户程序擅自在 `src.hpp` 中读入，可以在 `program` 的输出也加入完整性检测的 MD5，同时使用 `spj_bin` 或 `spj.cpp` 对 `program` 的输出进行检测，以防止用户程序擅自在 `src.hpp` 中输出。

  `"SPJ": 4` 相当于：

  ```json
    "SPJ": {
      "Compile": "hpp",
      "Run": "classic",
      "Check": "custom",
    }
  ```

- spj 5 output only

  这里将直接把用户提交的文件作为 `userOutput` 传递给 `spj_bin` 或 `spj.cpp`，如果你的 `spj_bin` 或 `spj.cpp` 中内置了一个编译器，理论上你可以支持所有程序语言的评测。关于 `spj_bin` 或 `spj.cpp`，具体参见 [自定义 Checker 部分](#自定义-checker)。

  `"SPJ": 5` 相当于：

  ```json
    "SPJ": {
      "Compile": "skip",
      "Run": "skip",
      "Check": "custom",
    }
  ```

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

**请不要将 `main.cpp` 以及 `src.hpp` 写在 `supportedFiles` 中！**

### Verilog

是否启用 Verilog 评测，启用为 `true`，否则为 `false` 。默认为 `false`。请注意，如果启用该选项，所有的提交的将会**强制**被视作 Verilog。关于 Verilog 评测的更多信息，请参阅 [Verilog 评测章节](#verilog-评测)。

### Quiz

是否是填选题，填选题为 `true`，否则为 `false`。默认为 `false`。

## I/O 交互题

评测 I/O 交互题时，将在一个评测机上同时运行选手提交的程序和题目提供的交互器（interactor），两者位于不同的沙箱中，仅可通过标准输入输出通信。选手的标准输出会接到交互器的标准输入，反之亦然。题目数据中的输入文件会从命令行传给交互器：

```sh
./interactor input output
```

```cpp
FILE *input   = fopen(argv[1], "r"); // 题目的输入文件
FILE *output  = fopen(argv[2], "w"); // 输出到此文件中
```

其中：

- input 是题目的输入文件（#.in），此文件对选手不可见。如果不存在输入文件则为 /dev/null。
- output 是输出。对此文件的输出会交给 checker 进行检查，若 Check=skip 则会直接作为评测结果：第一行应是一个 0 至 1 之间的数，表示得分占测试点总分的比例，0 为不得分，1 为满分（accepted），其余内容会作为测试点的评测消息展示给选手。

**注意：**为了使得评测能够进行下去，选手程序和裁判程序应当在输出每一行后主动 flush 输出流：例如 `fflush(stdout)` 或者使用 `std::cout << std::endl` 换行。否则，可能会导致交互死锁造成 TLE。

Interactor 可以为可执行文件或 C++ 源代码，可以在 config.json 中指定 interactor 的位置：

```json
  "SPJ": {
    "Run": {
      "Type": "interactive",
      "Interactor": {
        // 表示 interactor 为可执行文件，位于 zip 文件的 题号/interactor 路径下
        "Type": "binary",
        "Path": "interactor"
      }
    }
  }
```

```json
  "SPJ": {
    "Run": {
      "Type": "interactive",
      "Interactor": {
        // 表示 interactor 为 C++ 源码，位于 zip 文件的 题号/interactor.cpp 路径下
        "Type": "cpp",
        "Path": "interactor.cpp"
      }
    }
  }
```

如果不指定类型和位置，OJ 将使用 `interactor` （可执行文件）和 `interactor.cpp` （C++ 源码）作为 interactor 位置。

**注意：为保证数据包的兼容性，interactor 可执行文件应当是文本文件（使用 #! 的 shell/python 等脚本），不建议是二进制文件。**

对于 I/O 交互题，经常直接让 interactor 输出评测结果，而不使用另外的 checker。此时需要将 check 步骤指定为 skip：

```json
  "SPJ": {
    "Run": "interactive",
    "Check": "skip"
  }
```

在调试时，可以使用[交互题测试工具][test-interactive]进行测试。这个工具可以同时启动两个通过 I/O 进行交互的程序，同时可以输出两个程序之间的交互（需要 `-v` 选项）。这个工具也可以稍作改动后下发给学生。

[test-interactive]: /OnlineJudge/static/assets/test-interactive.py

![交互题测试工具](https://acm.sjtu.edu.cn/OnlineJudge/oj-images/e385707f-516d-4b73-9da0-cc42ded71745)

### testlib

Interactor 可以使用 testlib.h 编写，具体参见 [testlib.h 文档][testlib-interactor]。OJ 的编译环境中自带 testlib.h，无需在数据包中包含。本地调试时，请使用 [ACMOJ 专用的 testlib.h][testlib-acmoj]，不要使用 Codeforces/DOMjudge 等版本。

**注意：**默认情况下，testlib 会认为不使用另外的 checker，需要在 config.json 中指定 SPJ.Check = skip。如果需要使用 compare 或者自定义 checker，需要在调用 `registerInteraction` 时传入第三个参数为 false：

```cpp
registerInteraction(argc, argv, false);
```

以禁止 testlib 向输出文件写入评测结果。此时请使用 \_ok 退出，评测结果将被忽略，以 checker 输出的评测结果为准。如需给出评测信息，请写入到输出文件中，并使用自定义 checker。

Interactor 不支持传入答案文件（`ans`），请将需要传入的信息全部写入到输入文件中，或使用自定义 checker。

[testlib-interactor]: https://codeforces.com/blog/entry/18455
[testlib-acmoj]: https://github.com/ACMClassOJ/testlib

## 自定义 Checker

checker 会通过命令行（argv）传递参数，格式如下。

```sh
./checker input output answer score message
```

```cpp
FILE *input   = fopen(argv[1], "r"); // 题目的输入文件
FILE *output  = fopen(argv[2], "r"); // 用户输出
FILE *answer  = fopen(argv[3], "r"); // 题目的答案
FILE *score   = fopen(argv[4], "w"); // 把评测的分数输出到这里
FILE *message = fopen(argv[5], "w"); // 这里输出错误/提示信息
```

其中：

- input 是题目的输入文件。如果运行步骤被跳过，由于没有运行自然就没有输入，输入文件会传入 /dev/null。
- output 是选手程序的输出。如果运行步骤被跳过，则为选手程序本身。
- answer 是题目的答案（#.ans）。没有答案文件则会传入 /dev/null。
- score 是评测的分数。Checker 需要将分数写入此文件，应是一个 0 至 1 之间的数，表示得分占测试点总分的比例，0 为不得分，1 为满分（accepted）。
- message 是错误/提示信息。Checker 向此文件写入的内容将展示给选手。

Checker 可以为可执行文件或 C++ 源代码，可以在 config.json 中指定 checker 的位置：

```json
  "SPJ": {
    "Check": {
      "Type": "custom",
      "Checker": {
        // 表示 checker 为可执行文件，位于 zip 文件的 题号/checker 路径下
        "Type": "binary",
        "Path": "checker"
      }
    }
  }
```

```json
  "SPJ": {
    "Check": {
      "Type": "custom",
      "Checker": {
        // 表示 checker 为 C++ 源码，位于 zip 文件的 题号/checker.cpp 路径下
        "Type": "cpp",
        "Path": "checker.cpp"
      }
    }
  }
```

如果不指定类型和位置，OJ 将使用 `spj_bin` 和 `spj.cpp` 作为 checker 位置。

**注意：为保证数据包的兼容性，checker 可执行文件应当是文本文件（使用 #! 的 shell/python 等脚本），不建议是二进制文件。**

### testlib

Checker 可以使用 testlib.h 编写，具体参见 [testlib.h 文档][testlib-checker]。OJ 的编译环境中自带 testlib.h，无需在数据包中包含。本地调试时，请使用 [ACMOJ 专用的 testlib.h][testlib-acmoj]，不要使用 Codeforces/DOMjudge 等版本。

OJ 仅支持 \_ok 和 \_wa 两种评测结果，\_pe 和 \_fail 会认为是 \_wa。如果需要给出部分分，请使用 quitp，不支持 \_pc。

[testlib-checker]: https://codeforces.com/blog/entry/18431
