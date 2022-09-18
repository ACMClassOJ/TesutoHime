from asyncio import as_completed
from dataclasses import asdict
from logging import getLogger
from pathlib import PosixPath
from shutil import copy2
from typing import Dict, List, Tuple, Union

from gzip import GzipFile
import tarfile
import json

from commons.task_typing import FileUrl, RunResult
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
    except BaseException as e:
        logger.error(f'error removing temp dir {path}: {format_exc(e)}')

TempDir.config(working_dir, _judger_before_tmpdir_exit)


class InvalidProblemException(Exception): pass

async def copy_supplementary_files(files: List[FileUrl], cwd: PosixPath):
    if len(files) != 0:
        logger.debug(f'copying supplementary files to {cwd}')
    for f in as_completed(map(ensure_cached, files)):
        try:
            file = await f
            copy2(file.path, cwd / file.filename)
        except BaseException as e:
            msg = f'Cannot copy supplementary file: {format_exc(e)}'
            raise InvalidProblemException(msg) from e


def extract_exe_as_tar(exe: PosixPath):
    logger.debug(f'found artifact at {exe}, extracting as tarball')
    try:
        extracted = exe.parent / "extracted"
        gz_file = GzipFile(exe.as_posix())
        open(exe.parent / "extracted", "wb+").write(gz_file.read())
        gz_file.close()
        tar_file = tarfile.open(extracted.as_posix())
        tar_file.extractall(path = extracted.parent.as_posix())
    except BaseException as e:
        msg = f'Cannot untar: {format_exc(e)}'
        raise InvalidProblemException(msg) from e


def run_result_as_file(result: RunResult, dir: PosixPath) -> PosixPath:
    result_path = dir / "runres"
    try:
        with open(result_path.as_posix(), "w") as f:
            res_dict = asdict(result)
            res_dict.pop("input_path")
            res_dict.pop("output_path")
            f.write(json.dumps(res_dict))
        return result_path
    except BaseException as e:
        msg = f'Cannot record run result: {format_exc(e)}'
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
