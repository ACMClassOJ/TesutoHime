# Scheduler

*由于 scheduler 模块是第二代评测架构加入的内容，因此在此项目中，其也被称作 scheduler2。*

Scheduler 模块相关代码位于 [`scheduler2/`](../../scheduler2/) 目录下。本文档中，除非特殊说明，否则所有涉及的文件都以 `scheduler2` 目录为基础。

Scheduler 模块负责

- 分析题目 config，生成题目对应的评测材料，详见[生成题目对应的评测计划](#生成题目对应的评测计划)部分；
- 调度评测机，将任务分配给评测机，详见[评测代码](#评测代码)部分。

Scheduler 模块利用网络与其他模块进行通信，相关的模块包括[各评测机](judger.md)、[web 模块](web.md)、[Redis 数据库](redis.md)。

Scheduler 模块中，「任务」是一个广泛运用的概念，无论是生成评测计划的过程，还是评测代码的过程，都会涉及到任务的概念。

## 生成题目对应的评测计划

*关于生成的数据格式，请参阅 [`commons/task_typing.py`](../../commons/task_typing.py) 下的 `JudgerPlan` 类。*

当题目的数据包更新（或首次上传）时，scheduler 模块将会分析数据包的 config，并由此生成题目对应的评测计划，此部分的代码位于 [`scheduler2/plan.py`](../../scheduler2/plan.py)。关于数据包更新信息的获取，参见 web 模块下的[题目数据管理](web.md#题目数据管理)部分。

评测计划有四个部分：

- （可选）`compile`
- `judge`
- `score`
- （可选）`quiz`

### compile

*注意：compile 不是评测计划中必须的。*

如果题目需要有编译阶段，则会生成一个 `CompileTaskPlan`，其中包含了编译源文件、编译时限、编译内存限制信息。

### judge

`judge` 部分包含了若干个 `JudgeTaskPlan`，每个对应一组测试数据。其中包含了评测任务的计划、依赖信息。

### score

`score` 部分包含了若干个 `TestpointGroup`，每个对应一组测试数据。其中包含了计算分数相关的信息。

### quiz

*注意：quiz 不是评测计划中必须的。*

如果题目是 quiz，则会生成一个 `QuizProblem` 列表，其中包含了每题的信息。

## 评测代码

当有新的评测需求时，web 模块会向 scheduler 模块发送评测请求，scheduler 模块将会将评测任务分配给评测机（参见 [`scheduler2/dispatch.py](../../scheduler2/dispatch.py)），并将评测机的运行结果收集起来，储存在 judger Redis 数据库里。

如果在评测过程中发生了评测错误（如分配了评测任务的评测机掉线，任务执行超时，状态无法更新等），scheduler 会将任务重新分配给其他评测机。
