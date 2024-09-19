import logging.config
import sys
from logging.handlers import RotatingFileHandler
from settings import settings

for log in settings.LOGGERS:
    log_setup = logging.getLogger(log.get('name'))
    formatter = logging.Formatter(log.get('log_format'))
    file_handler = RotatingFileHandler(log.get('log_file'), maxBytes=5 * 1024 * 1024, backupCount=10)
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(formatter)
    log_setup.setLevel(log.get('log_level'))
    log_setup.addHandler(file_handler)
    log_setup.addHandler(stream_handler)

pidmr_logger = logging.getLogger('pidmr')
prm_logger = logging.getLogger('prm')
