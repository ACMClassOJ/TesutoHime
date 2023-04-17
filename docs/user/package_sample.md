# 数据包样例

by LauYeeYu，更新于 2023.2.16

*警告：错误的 json 将会导致各种意料之外的错误，因此在编辑时请务必确保格式符合！除非对 json 非常了解，或必须自定义 json，否则强烈建议使用数据 (GUI) 标签页下的下载 json 功能。*

- [SPJ 0](#spj-0)
- [SPJ 1](#spj-1)
- [SPJ 2](#spj-2)
- [SPJ 3](#spj-3)
- [SPJ 4](#spj-4)
- [SPJ 5](#spj-5)
- [文件共享](#文件共享)
- [Verilog](#verilog)

## SPJ 0
题号为 1 的普通题目共 4 个测试点，测试程序由提交者给出，测试点将检查测试程序在测试点输入 (`*.in`) 下的输出与所给出的标准输出 (`*.out`) 是否一致。

其中，1 和 3、2 和 4 的输入输出均是一样的，但 1、2 测试点无需内存泄漏检查，3、4 测试点需要内存泄漏检查。为了节约时间，建议将 1、2 的测试点分别设置为 3、4 测试点的依赖。

数据包结构如下：

```plain
1.zip
└── 1
    ├── 1.in
    ├── 1.out
    ├── 2.in
    ├── 2.out
    ├── 3.in
    ├── 3.out
    ├── 4.in
    ├── 4.out
    ├── config.json
    └── solution.cpp
```


## config.json
```json
{
    "Groups":[
        {
            "GroupID": 1,
            "GroupName": "naive test",
            "GroupScore": 25,
            "TestPoints": [
                1
            ]
        },
        {
            "GroupID": 2,
            "GroupName": "hard test",
            "GroupScore": 25,
            "TestPoints": [
                2
            ]
        },
        {
            "GroupID": 3,
            "GroupName": "naive test (memcheck)",
            "GroupScore": 25,
            "TestPoints":[
                3
            ]
        },
        {
            "GroupID": 4,
            "GroupName": "hard test (memcheck)",
            "GroupScore": 25,
            "TestPoints":[
                4
            ]
        }
    ],
    "Details": [
        {
            "ID": 1,
            "Dependency": 0,
            "TimeLimit": 1000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": false
        },
        {
            "ID": 2,
            "Dependency": 0,
            "TimeLimit": 1000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": false
        },
        {
            "ID": 3,
            "Dependency": 1,
            "TimeLimit": 1000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": true
        },
        {
            "ID": 4,
            "Dependency": 2,
            "TimeLimit": 1000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": true
        }
    ],
    "CompileTimeLimit": 10000,
    "SPJ": 0
}
```

## SPJ 1
题号为 2 的 SPJ 题目共 2 个测试点，由 `spj.cpp` 分析用户的输出结果后给出分数。

数据包结构如下：

```plain
2.zip
└── 2
    ├── 1.in
    ├── 1.out
    ├── 2.in
    ├── 2.out
    ├── config.json
    ├── solution.cpp
    └── spj.cpp
```

### spj.cpp
```cpp
#include <iostream>
#include <stdio.h>

int main(int argc, char *argv[]) {
    FILE *input = fopen(argv[1], "r"); // 题目的输入文件
    FILE *output = fopen(argv[2], "r"); // 用户输出
    FILE *answer = fopen(argv[3], "r"); // 题目的答案
    FILE *score = fopen(argv[4], "w"); // 把评测的分数输出到这里
    FILE *message = fopen(argv[5], "w"); // 这里输出错误/提示信息

    double n = 0.0; // 1 means 100%; 0.5 means 50%; 0 means 0%

    // code to give the score
    // ...

    fprintf(score, "%.2lf", n);
    return 0;
}
```

### config.json
```json
{
    "Groups": [
        {
            "GroupID": 1,
            "GroupName": "",
            "GroupScore": 50,
            "TestPoints": [
                1
            ]
        },
        {
            "GroupID": 2,
            "GroupName": "",
            "GroupScore": 50,
            "TestPoints": [
                2
            ]
        }
    ],
    "Details": [
        {
            "ID": 1,
            "Dependency": 0,
            "TimeLimit": 1000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": false
        },
        {
            "ID": 2,
            "Dependency": 0,
            "TimeLimit": 1000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": false
        }
    ],
    "CompileTimeLimit": 10000,
    "SPJ": 1
}
```

## SPJ 2
题号为 3 的 SPJ 题目共 2 个测试点，由 `*.cpp` 结合用户的输入文件（视作 `src.hpp`）运行并输出得分。

数据包结构如下：

```plain
3.zip
└── 3
    ├── 1.cpp
    ├── 2.cpp
    ├── config.json
    └── solution.hpp
```

### 1.cpp/2.cpp
*注：如果所有测试点的 C++ 代码都相同，可以只提供一个 `main.cpp` 文件。*
```cpp
#include <iostream>

#include "src.hpp"

int main() {
    double score = 0; // 1 means 100%; 0.5 means 50%; 0 means 0%

    // code to give the score
    // ...

    std::cout << score << std::endl;
    return 0;
}
```

### config.json
```json
{
    "Groups": [
        {
            "GroupID": 1,
            "GroupName": "",
            "GroupScore": 50,
            "TestPoints": [
                1
            ]
        },
        {
            "GroupID": 2,
            "GroupName": "",
            "GroupScore": 50,
            "TestPoints": [
                2
            ]
        }
    ],
    "Details": [
        {
            "ID": 1,
            "Dependency": 0,
            "TimeLimit": 1000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": false
        },
        {
            "ID": 2,
            "Dependency": 0,
            "TimeLimit": 1000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": false
        }
    ],
    "CompileTimeLimit": 10000,
    "SPJ": 2
}
```

## SPJ 3
题号为 4 的 SPJ 题目共 2 个测试点，由 `*.cpp` 结合用户的输入文件（视作 `src.hpp`）运行并输出，然后再与标准答案进行比较。

数据包结构如下：

```plain
4.zip
└── 4
    ├── 1.cpp
    ├── 1.in
    ├── 1.out
    ├── 2.cpp
    ├── 2.in
    ├── 2.out
    ├── config.json
    └── solution.hpp
```

### config.json
```json
{
    "Groups": [
        {
            "GroupID": 1,
            "GroupName": "",
            "GroupScore": 50,
            "TestPoints": [
                1
            ]
        },
        {
            "GroupID": 2,
            "GroupName": "",
            "GroupScore": 50,
            "TestPoints": [
                2
            ]
        }
    ],
    "Details": [
        {
            "ID": 1,
            "Dependency": 0,
            "TimeLimit": 1000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": false
        },
        {
            "ID": 2,
            "Dependency": 0,
            "TimeLimit": 1000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": false
        }
    ],
    "CompileTimeLimit": 10000,
    "SPJ": 3
}
```

## SPJ 4
题号为 5 的 SPJ 题目共 2 个测试点，由 `*.cpp` 结合用户的输入文件（视作 `src.hpp`）运行并输出，由 `spj.cpp` 根据输出结果给出分数。

数据包结构如下：

```plain
5.zip
└── 5
    ├── 1.cpp
    ├── 1.in
    ├── 1.out
    ├── 2.cpp
    ├── 2.in
    ├── 2.out
    ├── config.json
    ├── solution.hpp
    └── spj.cpp
```

### spj.cpp
```cpp
#include <iostream>

int main(int argc, char *argv[]) {
    FILE *input = fopen(argv[1], "r"); // 题目的输入文件
    FILE *output = fopen(argv[2], "r"); // 用户输出
    FILE *answer = fopen(argv[3], "r"); // 题目的答案
    FILE *score = fopen(argv[4], "w"); // 把评测的分数输出到这里
    FILE *message = fopen(argv[5], "w"); // 这里输出错误/提示信息

    double n = 0.0; // 1 means 100%; 0.5 means 50%; 0 means 0%

    // code to give the score
    // ...

    fprintf(score, "%.2lf", n);
    return 0;
}
```

### config.json
```json
{
    "Groups": [
        {
            "GroupID": 1,
            "GroupName": "",
            "GroupScore": 50,
            "TestPoints": [
                1
            ]
        },
        {
            "GroupID": 2,
            "GroupName": "",
            "GroupScore": 50,
            "TestPoints": [
                2
            ]
        }
    ],
    "Details": [
        {
            "ID": 1,
            "Dependency": 0,
            "TimeLimit": 1000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": false
        },
        {
            "ID": 2,
            "Dependency": 0,
            "TimeLimit": 1000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": false
        }
    ],
    "CompileTimeLimit": 10000,
    "SPJ": 4
}
```

## SPJ 5
题号为 6 的 SPJ 题目共 2 个测试点，由 `*.cpp` 结合用户的输入文件（视作 `src.hpp`）运行并输出，由 `spj.cpp` 根据输出结果给出分数。

数据包结构如下：

```plain
6.zip
└── 6
    ├── 1.in
    ├── 1.out
    ├── 2.in
    ├── 2.out
    ├── config.json
    ├── solution.hpp
    └── spj.cpp
```

### spj.cpp
```cpp
#include <iostream>

int main(int argc, char *argv[]) {
    FILE *input = fopen(argv[1], "r"); // 题目的输入文件
    FILE *output = fopen(argv[2], "r"); // 用户提交的文件
    FILE *answer = fopen(argv[3], "r"); // 题目的答案
    FILE *score = fopen(argv[4], "w"); // 把评测的分数输出到这里
    FILE *message = fopen(argv[5], "w"); // 这里输出错误/提示信息

    double n = 0.0; // 1 means 100%; 0.5 means 50%; 0 means 0%

    // code to give the score
    // ...

    fprintf(score, "%.2lf", n);
    return 0;
}
```

### config.json
```json
{
    "Groups": [
        {
            "GroupID": 1,
            "GroupName": "",
            "GroupScore": 50,
            "TestPoints": [
                1
            ]
        },
        {
            "GroupID": 2,
            "GroupName": "",
            "GroupScore": 50,
            "TestPoints": [
                2
            ]
        }
    ],
    "Details": [
        {
            "ID": 1,
            "Dependency": 0,
            "TimeLimit": 1000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": false
        },
        {
            "ID": 2,
            "Dependency": 0,
            "TimeLimit": 1000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": false
        }
    ],
    "CompileTimeLimit": 10000,
    "SPJ": 5
}
```

## 文件共享
题号为 6 的 SPJ 题目共 4 个测试点。其中，第 1 个测试点单独进行，第 2、3、4 个测试点共享文件，且需要按照顺序进行。最多只允许 20 个文件。

数据包结构如下：

```plain
6.zip
└── 6
    ├── 1.in
    ├── 1.out
    ├── 2.in
    ├── 2.out
    ├── 3.in
    ├── 3.out
    ├── 4.in
    ├── 4.out
    ├── config.json
    └── solution.cpp
```

### config.json
```json
{
    "Groups": [
        {
            "GroupID": 1,
            "GroupName": "Basic",
            "GroupScore": 1,
            "TestPoints": [
                1
            ]
        },
        {
            "GroupID": 2,
            "GroupName": "Persistence Test",
            "GroupScore": 1,
            "TestPoints": [
                2,
                3,
                4
            ]
        }
    ],
    "Details": [
        {
            "ID": 1,
            "Dependency": 0,
            "TimeLimit": 500,
            "MemoryLimit": 67108864,
            "DiskLimit": -1073741824,
            "FileNumberLimit": 20,
            "ValgrindTestOn": false
        },
        {
            "ID": 2,
            "Dependency": 0,
            "TimeLimit": 500,
            "MemoryLimit": 67108864,
            "DiskLimit": -1073741824,
            "FileNumberLimit": 20,
            "ValgrindTestOn": false
        },
        {
            "ID": 3,
            "Dependency": 2,
            "TimeLimit": 500,
            "MemoryLimit": 67108864,
            "DiskLimit": 1073741824,
            "FileNumberLimit": 20,
            "ValgrindTestOn": false
        },
        {
            "ID": 4,
            "Dependency": 3,
            "TimeLimit": 500,
            "MemoryLimit": 67108864,
            "DiskLimit": 1073741824,
            "FileNumberLimit": 20,
            "ValgrindTestOn": false
        }
    ],
    "CompileTimeLimit": 20000,
    "SPJ": 0,
    "Scorer": 0
}
```

## Verilog
题号为 7 的 Verilog 题目共 2 个测试点，由 `*.v` 结合用户的输入文件（视作 `answer.v`）运行并输出，然后再与标准答案进行比较。

数据包结构如下：

```plain
7.zip
└── 7
    ├── 1.v
    ├── 1.out
    ├── 2.v
    ├── 2.out
    └── config.json
```

### config.json
```json
{
    "Groups": [
        {
            "GroupID": 1,
            "GroupName": "1",
            "GroupScore": 60,
            "TestPoints": [
                1
            ]
        },
        {
            "GroupID": 2,
            "GroupName": "2",
            "GroupScore": 50,
            "TestPoints": [
                2
            ]
        }
    ],
    "Details": [
        {
            "ID": 1,
            "Dependency": 0,
            "TimeLimit": 3000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": false
        },
        {
            "ID": 2,
            "Dependency": 0,
            "TimeLimit": 3000,
            "MemoryLimit": 268435456,
            "DiskLimit": 0,
            "ValgrindTestOn": false
        }
    ],
    "CompileTimeLimit": 10000,
    "SPJ": 3,
    "Verilog": true
}
```
