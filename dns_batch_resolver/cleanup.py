#!/usr/bin/env python

""" remove useless domains from cachefile """

from db import DnsDB
from suxreadline import suxreadline

__author__ = 'oleg'


def cleanup():
    """ put domains in json dict with empty/default fields """
    db = DnsDB()
    domains_in_db = db.data.keys()
    domains_load = set(list(suxreadline()))
    for _domain in domains_load:
        domain = _domain.strip().decode('utf-8').encode('idna')
        if domain not in domains_in_db:
            db.entry_add(domain)
    for domain in db.data.keys():
        if domain not in domains_load:
            db.entry_del(domain)
    db.save()

if __name__ == '__main__':
    cleanup()
