# Judger

*由于目前 judger 模块已经迭代到第二代，因此其也被称作 judger2。*

Judger 模块相关代码位于 [`judger2/`](../../judger2/) 目录下。本文档中，除非特殊说明，否则所有涉及的文件都以 `judger2` 目录为基础。

## 评测流程

评测将分为三个步骤（位于 [`steps/`](../../judger2/steps/) 下：

1. 编译。此阶段中，会先准备好用户的文件，然后将题目的辅助文件拷贝到工作目录下（此过程会检查文件冲突）。具体参见 [`steps/compile_.py`](../../judger2/steps/compile_.py)。
1. 运行。具体参见 [`steps/run.py`](../../judger2/steps/run.py)。
1. 评分。具体参见 [`steps/check.py`](../../judger2/steps/check.py)。

## 沙箱

judger2 使用了沙箱技术，以保证评测机安全，并限制资源占用。具体参见 [sandbox 文档](sandbox.md)。

## 文件缓存

judger2 会将从 s3 上下载的文件缓存在本地，以减少对 s3 的访问。

如果缓存的文件在一天内没有被访问，judger2 会自动删除该文件。如果文件在一天内被访问了，judger2 会保留该文件。

## 评测机分组

评测机支持分组调度。在 `runner.yml` 配置中，`group` 项即为调度组，默认所有题目位于 `default` 组中。可以在题目配置中更改 `RunnerGroup` 来使该题目相关的任务被分配到对应的调度组，评测机不会运行其他组的任务。
