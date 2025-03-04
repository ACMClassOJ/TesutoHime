from asyncio import as_completed
from logging import getLogger
from pathlib import PosixPath
from shutil import copy2
from typing import Dict, List, Tuple, Union

from commons.task_typing import FileUrl
from commons.util import TempDir, format_exc

from judger2.cache import ensure_cached
from judger2.config import working_dir

logger = getLogger(__name__)


def _judger_before_tmpdir_exit(path: PosixPath):
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
        chown_back(path)
    except Exception as e:
        logger.error('error removing temp dir %(path)s: %(error)s', { 'path': path, 'error': e }, 'tempdir:remove')

TempDir.config(working_dir, _judger_before_tmpdir_exit)


class InvalidProblemException(Exception): pass
class FileConflictException(Exception): pass

async def copy_supplementary_files(files: List[FileUrl], cwd: PosixPath):
    if len(files) != 0:
        logger.debug('copying supplementary files to %(dest)s', { 'dest': cwd }, 'suppfiles:copy')
    for f in as_completed(map(ensure_cached, files)):
        try:
            file = await f
            dest = cwd / file.filename
            if dest.is_file():
                raise FileConflictException(f'File \'{file.filename}\' already exists')
            copy2(file.path, dest)
        except FileConflictException:
            raise
        except Exception as e:
            msg = f'Cannot copy supplementary file: {format_exc(e)}'
            raise InvalidProblemException(msg) from e


def format_args(args: Dict[str, Union[bool, str, List[str]]]) -> List[str]:
    def format_arg(arg: Tuple[str, Union[bool, str, List[str]]]):
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
