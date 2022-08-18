__all__ = ('task_logger',)

from logging import DEBUG, INFO, WARNING, Formatter, StreamHandler, getLogger, root
from logging.handlers import WatchedFileHandler
from pathlib import PosixPath

from config import log_dir

cwd = PosixPath(log_dir)

format = Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', '%c')

def add_handler (level, handler, target = root):
    handler.setLevel(level)
    handler.setFormatter(format)
    target.addHandler(handler)

add_handler(DEBUG, WatchedFileHandler(cwd / 'verbose.log'))
add_handler(INFO, WatchedFileHandler(cwd / 'judger.log'))
add_handler(WARNING, WatchedFileHandler(cwd / 'errors.log'))
add_handler(WARNING, StreamHandler())

task_logger = getLogger('tasks')
add_handler(INFO, WatchedFileHandler(cwd / 'tasks.log'), task_logger)
