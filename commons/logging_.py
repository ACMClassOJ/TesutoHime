__all__ = 'add_handler', 'setup_logging'

from logging import (DEBUG, INFO, NOTSET, WARNING, Formatter, LogRecord,
                     StreamHandler, root)
from logging.handlers import WatchedFileHandler
from pathlib import PosixPath
from re import sub
from os import environ

class RemoveSignaturesFormatter(Formatter):
    def __init__(self):
        super().__init__('%(asctime)s [%(levelname)s] %(name)s: %(message)s', '%c')
    def format(self, record):
        formatted = super().format(record)
        return sub('\?X-Amz.+\'', '\'', formatted)

def add_handler(level, handler, target = root):
    handler.setLevel(level)
    handler.setFormatter(RemoveSignaturesFormatter())
    handler.addFilter(no_boto_filter)
    target.addHandler(handler)

def no_boto_filter(record: LogRecord):
    if record.name.startswith('boto'):
        return 0
    return 1

def setup_logging(log_dir):
    cwd = PosixPath(log_dir)
    root.setLevel(NOTSET)

    add_handler(DEBUG, WatchedFileHandler(cwd / 'verbose.log'))
    add_handler(INFO, WatchedFileHandler(cwd / 'info.log'))
    add_handler(WARNING, WatchedFileHandler(cwd / 'errors.log'))
    output_level = DEBUG if environ.get('ENV') == 'development' else INFO
    add_handler(output_level, StreamHandler())
