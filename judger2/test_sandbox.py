from asyncio import CancelledError, Task, create_task, run, sleep
from shutil import which

from commons.task_typing import ResourceUsage
from judger2.util import TempDir
from judger2.sandbox import run_with_limits


async def autocancel (task: Task):
    await sleep(1)
    # task.cancel()

async def main ():
    run_task = create_task(run_test())
    create_task(autocancel(run_task))
    try:
        await run_task
    except CancelledError:
        print('task cancelled')

async def run_test ():
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
        bin_files = ['/bin', '/usr/bin', '/usr/include', '/usr/share/cmake']
        with open('test.out', 'w') as outfile:
            res = await run_with_limits(
                [which('cmake'), '.'], cwd, limits,
                supplementary_paths=bin_files,
                outfile=outfile,
            )
            print(res)
            if res.error != None: return
            res = await run_with_limits(
                [which('make')], cwd, limits,
                supplementary_paths=bin_files,
                outfile=outfile,
            )
            print(res)
            if res.error != None: return
            res = await run_with_limits([str(exe)], cwd, limits, outfile=outfile)
            print(res)

if __name__ == '__main__':
    run(main())
