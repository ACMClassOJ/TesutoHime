from asyncio import get_running_loop, as_completed
from logging import getLogger
from pathlib import PosixPath
from shutil import copy2, rmtree
from typing import Callable, Dict, List, TypeVar, Union
from uuid import uuid4

from judger2.config import working_dir
from judger2.cache import ensure_cached
from commons.task_typing import Url

logger = getLogger(__name__)


T = TypeVar('T')

async def asyncrun (func: Callable[[], T]) -> T:
    return await get_running_loop().run_in_executor(None, func)


class TempDir:
    path: PosixPath
    def __init__ (self):
        self.path = PosixPath(working_dir) / str(uuid4())
    def __enter__ (self) -> PosixPath:
        logger.debug(f'entering temp dir {self.path}')
        self.path.mkdir()
        self.path.chmod(0o770)
        return self.path
    def __exit__ (self, *_args):
        logger.debug(f'exiting temp dir {self.path}')
        # import here to avoid circular reference
        from judger2.sandbox import chown_back
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
            logger.error(f'error removing temp dir {self.path}: {e}')


async def copy_supplementary_files (files: List[Url], cwd: PosixPath):
    if len(files) != 0:
        logger.debug(f'copying supplementary files to {cwd}')
    for f in as_completed(map(ensure_cached, files)):
        file = await f
        copy2(file.path, cwd / file.filename)


def format_args (args: Dict[str, Union[bool, str, List[str]]]) -> List[str]:
    def format_arg (arg: tuple[str, Union[bool, str, List[str]]]):
        k, v = arg
        k = f'--{k}'
        if v is True:
            return [k]
        if v is False:
            return []
        if isinstance(v, list):
            return sum(map(lambda x: [k, x], v), [])
        return [k, v]
    return sum(map(format_arg, args.items()), [])
