from asyncio import as_completed
from os import utime
from pathlib import PosixPath
from shutil import copy2
from uuid import uuid4

from cache import ensure_cached, upload
from config import cache_dir
from ...sandbox import chown_back
from steps.compile.cpp import compile_cpp
from steps.compile.git import compile_git
from steps.compile.verilog import compile_verilog
from task import InvalidTaskException
from task_typing import CompileLocalResult, CompileResult, CompileTask
from util import TempDir


async def compile (task: CompileTask) -> CompileLocalResult:
    with TempDir() as cwd:
        # copy supplementary files
        for f in as_completed(map(ensure_cached, task.supplementary_files)):
            file = await f
            copy2(file.path, cwd / file.filename)

        # compile
        type = task.source.type
        # The compiled program returned by these functions
        # reside inside cwd. As cwd is deleted once this
        # function returns, the file need to be uploaded or
        # cached for later use, and the cache location is
        # returned as a semi-persistent compile artifact
        # location.
        if type == 'cpp':
            res = await compile_cpp(cwd, task.source, task.limits)
        elif type == 'git':
            res = await compile_git(cwd, task.source, task.limits)
        elif type == 'verilog':
            res = await compile_verilog(cwd, task.source, task.limits)
        else:
            raise InvalidTaskException(f'compile: invalid source type {type}')

        # check for errors
        if res.result.result != 'compiled':
            return res
        if res.local_path == None:
            return CompileLocalResult(
                result=CompileResult(
                    result='system_error',
                    message='compilation succeeded without artifact'
                ),
                local_path=None
            )
        # Chown back, or else we probably couldn't copy the
        # artifact in case the file is of mode like 0700
        # set by the compiler or by a bad mask.
        chown_back(cwd)

        # upload artifacts
        if task.artifact != None:
            local_path = (await upload(res.local_path, task.artifact.url)).path
        else:
            local_path = PosixPath(cache_dir) / str(uuid4())
            copy2(res.local_path, local_path)
            # touch the local file so the file will be eventually deleted
            utime(local_path)

        # done
        return CompileLocalResult(result=res.result, local_path=local_path)
