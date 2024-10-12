#!/usr/bin/python3

from asyncio import (create_subprocess_exec, create_task, get_running_loop,
                     run, wait)
from errno import EAGAIN, EPIPE
from os import close, pipe, read, set_blocking, write
from sys import argv, stdout

helptext = f'''
Usage:
    {argv[0]} [-v] <program A> [program A args...] -- <program B> [program B args...]

Example:
    {argv[0]} ./code -- ./interactor 1.in 1.out

Options:
    -v: print all activity between two programs
'''.strip()

verbose = False

def help():
    print(helptext)
    exit(1)

def parse_args():
    args = argv[1:]
    if len(args) < 1:
        help()
    if args[0] == '-v':
        args = args[1:]
        global verbose
        verbose = True

    argv1 = []
    while len(args) > 0 and args[0] != '--':
        argv1.append(args[0])
        args = args[1:]
    if len(args) < 2 or len(argv1) < 1:
        help()
    args = args[1:]

    return argv1, args

async def runprog(argv, stdin, stdout):
    proc = await create_subprocess_exec(argv[0], *argv[1:], stdin=stdin, stdout=stdout)
    close(stdin)
    close(stdout)
    await proc.wait()

class Break(BaseException): pass

def connect(prefix: bytes, r: int, w: int):
    set_blocking(r, False)
    set_blocking(w, False)

    def connectsync():
        line = [b'', False]
        def flush():
            if not verbose:
                line[0] = b''
                return
            s = prefix
            if line[0] == b'':
                return
            if line[1]:
                s += '\x1b[2m…\x1b[0m'.encode()
            else:
                s += b' '
            line[1] = not line[0].endswith(b'\n')
            if not line[1]:
                line[0] = line[0][:-1] + '\x1b[2m↵\x1b[0m'.encode()
            s += line[0]
            if line[1]:
                s += '\x1b[2m…\x1b[0m'.encode()
            stdout.buffer.write(s + b'\n')
            stdout.buffer.flush()
            line[0] = b''

        def do_read():
            try:
                c = read(r, 1)
            except OSError as err:
                if err.errno == EAGAIN:
                    flush()
                    set_blocking(r, True)
                    c = do_read()
                    set_blocking(r, False)
                else:
                    raise
            if c is None or len(c) == 0:
                raise Break
            return c

        def do_write(b: bytes):
            try:
                write(w, b)
            except OSError as err:
                if err.errno == EAGAIN:
                    flush()
                    set_blocking(w, True)
                    do_write(b)
                    set_blocking(w, False)
                elif err.errno == EPIPE:
                    raise Break
                else:
                    raise

        try:
            while True:
                c = do_read()
                line[0] += c
                set_blocking(r, False)
                if c == b'\n':
                    flush()
                do_write(c)
        except Break:
            close(r)
            close(w)

    loop = get_running_loop()
    return loop.run_in_executor(None, connectsync)

'''
pipe architecture:
          A   |      me      |   B
 (stdin) r1a <-- w1a <~ r1b <-- w1b (stdout)
(stdout) w2a --> r2a ~> w2b --> r2b (stdin)
'''

async def main(argv1, argv2):
    r1a, w1a = pipe()
    r1b, w1b = pipe()
    r2a, w2a = pipe()
    r2b, w2b = pipe()
    prog1 = create_task(runprog(argv1, r1a, w2a))
    prog2 = create_task(runprog(argv2, r2b, w1b))
    ct1 = connect(b'\x1b[1;31m<\x1b[0m', r1b, w1a)
    ct2 = connect(b'\x1b[1;32m>\x1b[0m', r2a, w2b)
    await wait([prog1, prog2, ct1, ct2])

if __name__ == '__main__':
    try:
        run(main(*parse_args()))
    except KeyboardInterrupt:
        exit(1)
