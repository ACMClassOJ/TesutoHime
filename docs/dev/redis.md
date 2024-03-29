# Redis

## 消息队列

评测机和调度机之间通过一系列 Redis 消息队列来通信。以下假设
prefix 为 oj，则这些消息队列有:

- `oj-tasks`: 字符串数组, 存储所有待评测的 Task ID
- 对于每台评测机:
  - `oj-heartbeat-runner%d`: float，存储最后上线时间
  - `oj-in-progress-runner%d`: 长度为 1 的字符串数组, 存储当前正在评测的 Task ID
- 对于每个评测任务: (Task ID 是一个 UUIDv4)
  - `oj-task-task-%s`: Task, 存储序列化过的任务内容
  - `oj-task-progress-%s`: StatusUpdate 数组, 存储评测机给调度机发的消息
  - `oj-task-abort-%s`: 调度机向这里 lpush 表示中断这个 Task

Task 的具体类型见 commons.task_typing 模块里的类型定义。

## 常见 Redis 命令解释

- get: 获取一个字符串。
- set: 把一个 key 设置为一个字符串。
- del: 删除一个 key。
- lpush: 向一个数组的大端推一个值。
- lpop: 从一个数组的大端取出一个值，若数组为空则返回 null / None。
- blpop: 从一个数组的大端取出一个值，若数组为空则暂时阻塞，直到数组不为空。
  若有多个 blpop 阻塞在同一个 key 上时，这个 key 被 push 进来了一个值，
  则只有一个 blpop 会返回，其他会继续阻塞。
- lrem: 从一个数组里删除一个值。
- brpoplpush: 从一个数组的一端取出一个值，推到另一个数组的一端。
  若取值的数组为空则暂时阻塞。
  若有多个 brpoplpush 阻塞在同一个 key 上时，这个 key 被 push 进来了一个值，
  则只有一个 brpoplpush 会返回，其他会继续阻塞。
- expire: 使一个 key 在若干秒后被删除。
