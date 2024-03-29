# Asyncio

judger2 和 scheduler2 使用了 [asyncio] 来实现任务的并发处理。
与传统的利用多个线程来执行并行任务不同，asyncio 只使用主线程来处理主要逻辑，
而利用异步操作 (`async`/`await`) 和基于 [事件循环][evloop]
的任务调度来实现并行。简而言之，就是说业务逻辑全部在一个线程里执行。

这样做的好处有不少，例如可以轻易取消任务、很多时候不用考虑线程安全性、
避免线程切换带来的性能损失等等。但是，如果写代码的时候不注意，
就会导致整个事件循环阻塞而导致整个程序的 (而不只是单个线程的)
阻塞。例如，如果这样写:

```python
from shutil import copy

async def copy_input (problem_id, testpoint_id):
    copy(f'/cache/{problem_id}/{testpoint_id}.in', '/tmp/input')
```

而这个输入文件很大的话 (经常有题目输入文件有几十到几百 MiB),
就会导致整个程序阻塞，这段时间里整个程序都不能处理任何其他事情。
一般来说，如果一个有可能运行时间很长的任务代码前面没有 `await`,
就表明可能会导致阻塞。

如果在写代码的时候碰到了这样可能会导致性能问题的函数，可以这样做:

1. 查一下是否有支持 asyncio 的替代性 API。例如，用 [aiohttp]
   代替 [requests] 和 [Flask][flask]。一般搜索关键词「python
   asyncio API名称」即可。
2. 使用 `commons.util` 里提供的 `asyncrun` 函数。这个函数会新开一个线程
   (实际上是使用一个线程池) 执行阻塞 API，然后在线程执行完成之后返回。
   例如:

   ```python
   copy(src, dst)
   # 替换为 ↓
   from commons.util import asyncrun
   await asyncrun(lambda: copy(src, dst))
   ```

[asyncio]: https://docs.python.org/3/library/asyncio.html
[evloop]: https://docs.python.org/3/library/asyncio-eventloop.html
[aiohttp]: https://docs.aiohttp.org/en/stable/
[requests]: https://requests.readthedocs.io/en/latest/
[flask]: https://flask.palletsprojects.com/en/latest/
