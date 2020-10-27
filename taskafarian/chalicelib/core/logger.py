import logging
import os
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')

# to stdout
to_stdout = logging.StreamHandler()
to_stdout.setFormatter(formatter)
logger.addHandler(to_stdout)

# to file
if os.getenv('TASKAFARIAN_ENABLE_LOG_TO_FILE') == 'True':
    to_file = RotatingFileHandler(filename='app.log', maxBytes=1 * 1024 * 10, backupCount=5)
    to_file.setFormatter(formatter)
    logger.addHandler(to_file)

log_level = logging.DEBUG if os.getenv('TASKAFARIAN_DEBUG') == 'True' else logging.INFO
logger.setLevel(log_level)
