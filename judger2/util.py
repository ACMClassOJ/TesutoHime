import asyncio
from pathlib import PosixPath
from shutil import rmtree
from typing import Callable, TypeVar
from uuid import uuid4

from config import working_dir


T = TypeVar('T')

async def asyncrun (func: Callable[[], T]) -> T:
    return await asyncio.get_running_loop().run_in_executor(None, func)


class TempDir:
    path: PosixPath
    def __init__ (self):
        self.path = PosixPath(working_dir) / str(uuid4())
    def __enter__ (self) -> PosixPath:
        self.path.mkdir()
        self.path.chmod(0o770)
        return self.path
    def __exit__ (self, *_args):
        # import here to avoid circular reference
        from sandbox import chown_back
        try:
            # Why chown_back:
            # There may be some subdirtectories in the temp
            # dir that are created by the worker process.
            # In that case, these dirs are owned by the
            # worker user, not the current user, thus rmtree
            # would fail on these files. However, we could
            # create a new namespace and chown these things
            # back to our user, so these files could be
            # removed by rmtree.
            chown_back(self.path)
            rmtree(self.path, ignore_errors=True)
        except Exception as e:
            print(f'error removing temp dir {self.path}:', e)
