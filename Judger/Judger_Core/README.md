## 评测核心

### 接口说明：

#### ProblemSubtaskConfig

| 成员        | 备注                                             |
| ----------- | ------------------------------------------------ |
| inputFiles  | 测试点的读入文件，以文件指针列表的形式传入       |
| outputFiles | 测试点的答案文件，以文件指针列表的形式传入       |
| timeLimit   | 每个测试点统一的时间限制，单位：ms，整数类型     |
| memoryLimit | 每个测试点统一的内存空间限制，单位：kb，整数类型 |
| diskLimit   | 每个测试点统一的磁盘空间限制，单位：kb，整数类型 |

#### ProblemConfig

| 成员             | 备注                                             |
| ---------------- | ------------------------------------------------ |
| sourceCode       | 以字符串形式储存的源代码                         |
| language         | 源代码所使用的语言                               |
| compileTimeLimit | 编译时长限制，单位：ms                           |
| subtasks         | list[ProblemSubtaskConfig]，子任务配置信息的列表 |
| SPJ              | 以字符串形式储存的SPJ源代码                      |

#### JudgeTestPointResult - 单一测试点的测试结果

| 成员  | 备注                                        |
| ----- | ------------------------------------------- |
| stat  | 测试结果状态，字符串类型                    |
| score | 测试点分数，整数类型，由spj给出             |
| msg   | 测试点结果的相关信息，字符串类型，由spj给出 |
| time  | 运行用时，单位：ms，整数类型                |
| mem   | 占用内存空间，单位：kb，整数类型            |
| disk  | 占用磁盘空间，单位：kb，整数类型            |

#### JudgeSubtaskResult - 子任务的测试结果

| 成员       | 备注                                         |
| ---------- | -------------------------------------------- |
| testPoints | list[JudgeTestPointResult], 测试点的结果列表 |
| stat       | 子任务测试结果状态，字符串类型               |
| score      | 子任务分数，整数类型                         |

#### JudgeResult - 一份提交的测试结果

| 成员     | 备注                                       |
| -------- | ------------------------------------------ |
| subtasks | list[JudgeSubtaskResult], 子任务的结果列表 |

#### JudgeCore -评测核心

| 成员          | 备注                                               |
| ------------- | -------------------------------------------------- |
| problemConfig | 所需评测的题目配置以及选手代码                     |
| judge()       | 评测选手的代码，得到评测结果，返回值为 JudgeResult |

# 安装 seccomp
```
sudo apt install libseccomp-dev libseccomp2 seccomp
```