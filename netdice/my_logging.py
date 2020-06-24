import contextlib
import json
import logging
import logging.config
import os
import sys
import time

from netdice.util import project_root_dir

# LOG LEVELS
# existing:
# CRITICAL = 50
# ERROR = 40
# WARNING = 30
# INFO = 20
# DEBUG = 10
DATA = 5


class OnlyDataFilter(logging.Filter):
    def filter(self, record):
        return record.levelno == DATA


class NoErrorFilter(logging.Filter):
    def filter(self, record):
        return record.levelno <= logging.WARNING


class MyLogging:
    def __init__(self):
        logging.addLevelName(DATA, "DATA")
        logging.config.dictConfig({'version': 1})  # must call initialize first
        self.is_initialized = False
        self.context = []

    # initialize the logger
    def initialize(self, stdout_level: str, log_file=None, data_log_file=None, file_level='INFO'):
        if self.is_initialized:
            self.error("cannot initialize logger multiple times")
            exit(1)
        self.is_initialized = True

        log_dir = os.path.join(project_root_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        if log_file is None:
            log_file = os.path.join(log_dir, 'netoracle_debug.log')

        if data_log_file is None:
            data_log_file = os.path.join(log_dir, 'netoracle_data.log')

        default_logging = {
            'version': 1,
            'formatters': {
                'full': {
                    'format': '%(asctime)s [%(levelname)5s]: %(message)s',
                    'datefmt': '%Y-%m-%d_%H-%M-%S'
                },
                'standard': {
                    'format': '[%(levelname)5s] %(message)s',
                },
                'minimal': {
                    'format': '%(message)s'
                },
            },
            'filters': {
                'onlydata': {
                    '()': OnlyDataFilter
                },
                'noerrors': {
                    '()': NoErrorFilter
                }
            },
            'handlers': {
                'stdout': {
                    'level': stdout_level,
                    'formatter': 'standard',
                    'class': 'logging.StreamHandler',
                    'stream': sys.stdout,
                    'filters': ['noerrors']
                },
                'stderr': {
                    'level': 'ERROR',
                    'formatter': 'standard',
                    'class': 'logging.StreamHandler',
                    'stream': sys.stderr
                },
                'filedebug': {
                    'level': file_level,
                    'formatter': 'full',
                    'filename': log_file,
                    'mode': 'w',
                    'class': 'logging.FileHandler'
                },
                'filedata': {
                    'level': 'DATA',
                    'formatter': 'minimal',
                    'filename': data_log_file,
                    'mode': 'w',
                    'class': 'logging.FileHandler',
                    'filters': ['onlydata']
                }
            },
            'loggers': {
                '': {
                    'handlers': ['stdout', 'stderr', 'filedebug', 'filedata'],
                    'level': 0
                }
            }
        }
        logging.config.dictConfig(default_logging)

    def critical(self, msg, *args, **kwargs):
        logging.critical(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        logging.error(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        logging.warning(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        logging.info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        logging.debug(msg, *args, **kwargs)

    def data(self, key, value):
        d = {"ctx": self.context, key: value}
        return logging.log(DATA, json.dumps(d))


log = MyLogging()


@contextlib.contextmanager
def log_context(key):
    log.context.append(key)
    yield
    log.context.pop()


@contextlib.contextmanager
def time_measure(key):
    start = time.time()
    yield
    end = time.time()
    elapsed = end - start
    log.data(key, elapsed)
