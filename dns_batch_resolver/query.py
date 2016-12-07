#!/usr/bin/env python
""" print ipv4 or ipv6 from resolv cache if they in https.resolv """

from sys import argv
from db import DnsDB
from config import CONFIG
from suxreadline import suxreadline

__author__ = 'oleg'


def query():
    db = DnsDB(db_file=CONFIG['CACHEFILE_HOT'], proto='pickle')
    mode = 'ip6' in argv and 'ip6' or 'ip'
    for domain in suxreadline():
        for ip in db.data.get(domain, {}).get(mode, {}).keys():
            print ip

if __name__ == '__main__':
    query()
