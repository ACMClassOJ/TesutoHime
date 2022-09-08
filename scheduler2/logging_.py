__all__ = ()

from logging import INFO, getLogger
from logging.handlers import WatchedFileHandler

from commons.logging_ import add_handler, setup_logging

from scheduler2.config import log_dir

setup_logging(log_dir)

access_logger = getLogger('aiohttp.access')
access_logger.propagate = False
access_log_file = log_dir / 'access.log'
add_handler(INFO, WatchedFileHandler(access_log_file), access_logger)
