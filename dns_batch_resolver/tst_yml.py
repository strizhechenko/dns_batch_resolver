from os import getenv
import yaml

__config_filename__ = getenv('CONFIG', '/etc/dns_batch_resolver.conf')
__config_filename__ = 'dns_batch_resolver.conf'

CONFIG = yaml.load(open(__config_filename__).read())

print CONFIG
