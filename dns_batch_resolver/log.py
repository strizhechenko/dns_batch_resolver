import logging
from config import CONFIG

log = logging.getLogger('qdns')
log_level = logging.INFO
if CONFIG['RESOLVER_DEBUG'] == '1':
    log_level = logging.DEBUG
    logging.basicConfig(format='%(asctime)-15s %(message)s', level=log_level)
