__all__ = ('log_request',)

import time
from logging import INFO, getLogger
from logging.handlers import WatchedFileHandler
from pathlib import PosixPath
from typing import Any, Dict

from flask import g, request
from sqlalchemy import event
from sqlalchemy.engine import Engine

from commons.logging_ import add_handler, setup_logging
from web.config import LogConfig

setup_logging(LogConfig.log_dir)

access_logger = getLogger('web.access')
access_log_file = PosixPath(LogConfig.log_dir) / 'access.log'
add_handler(INFO, WatchedFileHandler(access_log_file), access_logger)

logger = getLogger(__name__)

def log_request():
    if 'skip_logging' in g and g.skip_logging: return

    for k in g.timings:
        g.timings[k] = round(g.timings[k], 4)

    post_args = request.form.copy()
    for k in post_args:
        if 'password' in k:
            post_args[k] = '***'
    if 'code' in post_args: del post_args['code']

    entry: Dict[Any, Any] = {
        'ip': request.remote_addr,
        'time': g.time.isoformat(),
        'username': None,
        'realname': None,
        'method': request.method,
        'url': '/'.join(request.url.split('/')[4:]),
        'args': request.args,
        'post_args': post_args,
        'timings': g.timings,
    }
    if 'user_username' in g:
        entry['username'] = g.user_username
        entry['realname'] = g.user_realname
    if 'token' in g and g.token is not None:
        entry['token_id'] = g.token.id
        entry['app_id'] = g.token.app_id

    access_logger.info('%(ip)s - %(username)s - %(realname)s "%(method)s /%(url)s"', entry, 'access')


@event.listens_for(Engine, 'before_cursor_execute')
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())


seen_slow_statements = set()

@event.listens_for(Engine, 'after_cursor_execute')
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    g.timings['sql'] += total
    g.timings['sqlcount'] += 1
    if total > 0.1:  # 100 ms
        statement_str = str(statement)
        if statement_str not in seen_slow_statements:
            seen_slow_statements.add(statement_str)
            logger.info('SQL statement %(statement)s took %(time)s seconds', { 'statement': statement_str, 'time': total }, 'sql:slow')
