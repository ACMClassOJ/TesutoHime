__all__ = 'add_handler', 'setup_logging'

import json
from dataclasses import is_dataclass
from datetime import datetime
from logging import (DEBUG, INFO, NOTSET, WARNING, Formatter, LogRecord,
                     StreamHandler, root)
from logging.handlers import WatchedFileHandler
from os import environ
from pathlib import PosixPath
from re import compile

from commons.util import format_exc


class JsonFormatter(Formatter):
    def __init__(self, json_output = False):
        super().__init__('%(message)s', '%c')
        self.x_amz_regex = compile('\?X-Amz.+')
        self.json_output = json_output

    def serialize(self, object):
        if isinstance(object, BaseException):
            return self.remove_signatures(format_exc(object))
        if isinstance(object, str):
            return self.remove_signatures(object)
        if isinstance(object, (int, float, bool)) or object is None:
            return object
        if isinstance(object, list):
            return list(map(self.serialize, object))
        if isinstance(object, dict):
            return { k: self.serialize(v) for k, v in object.items() }
        if not is_dataclass(object):
            return self.remove_signatures(str(object))
        return { k: self.serialize(v) for k, v in object.__dict__.items() } + { '$type': object.__class__.__name__ }

    def remove_signatures(self, msg):
        return self.x_amz_regex.sub('\'', msg)

    def format(self, record):
        entry = {
            'time': datetime.fromtimestamp(record.created).isoformat(),
            'logger': record.name,
            'level': record.levelname,
            'filename': record.filename,
            'funcname': record.funcName,
            'lineno': record.lineno,
        }
        if len(record.args) == 2 and isinstance(record.args[0], dict) and isinstance(record.args[1], str):
            args = record.args[0]
            entry['type'] = record.args[1]
            entry['message'] = record.msg % args
            entry['args'] = { k: self.serialize(v) for k, v in args.items() }
        else:
            if record.name == 'aiohttp.access':
                args = {}
                for k in 'remote_address', 'first_request_line', 'response_status', 'response_size':
                    args[k] = record.__dict__[k]
                entry['args'] = args
            entry['message'] = record.getMessage()

        if self.json_output:
            return json.dumps(entry, ensure_ascii=False)
        else:
            record.message = entry['message']
            record.asctime = self.formatTime(record)
            return '%(asctime)s [%(levelname)s] %(name)s: %(message)s' % record.__dict__

def add_handler(level, handler, target = root, json_output = False):
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter(json_output))
    handler.addFilter(no_boto_filter)
    target.addHandler(handler)

def no_boto_filter(record: LogRecord):
    if record.name.startswith('boto'):
        return 0
    return 1

def setup_logging(log_dir):
    cwd = PosixPath(log_dir)
    root.setLevel(NOTSET)

    add_handler(DEBUG, WatchedFileHandler(cwd / 'raw.log'), json_output=True)
    add_handler(DEBUG, WatchedFileHandler(cwd / 'verbose.log'))
    add_handler(INFO, WatchedFileHandler(cwd / 'info.log'))
    add_handler(WARNING, WatchedFileHandler(cwd / 'errors.log'))
    output_level = DEBUG if environ.get('ENV') == 'development' else INFO
    add_handler(output_level, StreamHandler())
