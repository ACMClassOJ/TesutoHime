# Judger

*由于目前 judger 模块已经迭代到第二代，因此其也被称作 judger2。*

Judger 模块相关代码位于 [`judger2/`](../../judger2/) 目录下。本文档中，除非特殊说明，否则所有涉及的文件都以 `judger2` 目录为基础。

## 评测流程

评测将分为三个步骤（位于 [`steps/`](../../judger2/steps/) 下：

1. 编译。具体参见 [`steps/compile_.py`](../../judger2/steps/compile_.py)。
1. 运行。具体参见 [`steps/run.py`](../../judger2/steps/run.py)。
1. 评分。具体参见 [`steps/check.py`](../../judger2/steps/check.py)。

## 沙箱

judger2 使用了沙箱技术，以保证评测机安全，并限制资源占用。具体参见 [sandbox 文档](sandbox.md)。

## 文件缓存

judger2 会将从 s3 上下载的文件缓存在本地，以减少对 s3 的访问。

如果缓存的文件在一天内没有被访问，judger2 会自动删除该文件。如果文件在一天内被访问了，judger2 会保留该文件。
