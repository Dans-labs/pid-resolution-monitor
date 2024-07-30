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

# NOTSET=0
# DEBUG=10
# INFO=20
# WARN=30
# ERROR=40
# CRITICAL=50

#     logger.propagate = False
#
#     logging.getLogger("httpx").setLevel(logging.WARNING)
#     logging.getLogger("httpcore").setLevel(logging.WARNING)
#     logging.getLogger("watchfiles").setLevel(logging.WARNING)
#     logging.getLogger('passlib').setLevel(logging.ERROR)
