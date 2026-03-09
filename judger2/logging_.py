__all__ = ('task_logger',)

from logging import INFO, getLogger
from logging.handlers import WatchedFileHandler
from pathlib import PosixPath

from commons.logging_ import add_handler, setup_logging

from judger2.config import config

setup_logging(str(config.log_dir))

task_logger = getLogger('tasks')
taskslog_file = PosixPath(config.log_dir) / 'tasks.log'
add_handler(INFO, WatchedFileHandler(taskslog_file), task_logger)
