# coding: utf-8

from os import getenv
from datetime import datetime
import yaml

__config_filename__ = getenv('CONFIG', '/etc/dns_batch_resolver.conf')

CONFIG = yaml.load(open(__config_filename__).read())
assert isinstance(CONFIG.get('production'), bool)
assert isinstance(CONFIG.get('MIN_TTL'), int)
assert isinstance(CONFIG.get('MAX_TTL'), int)
assert isinstance(CONFIG.get('NXDOMAIN_TTL'), int)
assert isinstance(CONFIG.get('IP_TTL'), int)
assert isinstance(CONFIG.get('RESOLVER_LIMIT'), int)
assert isinstance(CONFIG.get('RESOLVER_DEBUG'), bool)
assert isinstance(CONFIG.get('BLACKHOLES'), list)
assert isinstance(CONFIG.get('CACHEFILE'), str)
assert isinstance(CONFIG.get('CACHEFILE_HOT'), str)

CURRENT_UNIXTIME = lambda: int(datetime.now().strftime("%s"))

if __name__ == '__main__':
    print CONFIG

#
# DNS_BLACKHOLES = ['127.0.0.1', '95.213.143.204']
# if os.environ.get('DNS_BLACKHOLE_IP'):
#     DNS_BLACKHOLES.append(os.environ.get('DNS_BLACKHOLE_IP'))
#
# if not PRODUCTION:
#     MAIN_DIR = os.getcwd() + '/'
#
