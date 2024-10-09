from asyncio import CancelledError, Task, create_task, run, sleep

from commons.task_typing import ResourceUsage

from judger2.sandbox import run_with_limits
from judger2.util import TempDir


async def autocancel(task: Task):
    await sleep(1)
    # task.cancel()

async def main():
    run_task = create_task(run_test())
    create_task(autocancel(run_task))
    try:
        await run_task
    except CancelledError:
        print('task aborted')

async def run_test():
    with TempDir() as cwd:
        cpp = cwd / 'main.c'
        exe = cwd / 'code'
        cpp.write_text(r'''
#include <stdio.h>

int main () {
    while (1);
    printf("Hello World!\n");
    return 0;
}
''')
        cmf = cwd / 'CMakeLists.txt'
        cmf.write_text('''
project(test)
set(CMAKE_EXPORT_COMPILE_COMMANDS true)
add_executable(code main.c)
''')
        limits = ResourceUsage(
            time_msecs=2000,
            memory_bytes=104857600,
            file_count=100,
            file_size_bytes=1048576,
        )
        with open('test.out', 'w') as outfile:
            res = await run_with_limits(
                'std', ['/bin/cmake', '.'], cwd, limits,
                outfile=outfile,
            )
            print(res)
            if res.error is not None: return
            res = await run_with_limits(
                'std', ['/bin/make'], cwd, limits,
                outfile=outfile,
            )
            print(res)
            if res.error is not None: return
            res = await run_with_limits('libc', [str(exe)], cwd, limits, outfile=outfile)
            print(res)

if __name__ == '__main__':
    run(main())
