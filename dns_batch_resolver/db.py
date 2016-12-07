#!/usr/bin/env python
# coding: utf-8
"""
Смесь резолвера с методами для работы с базой,
потом надо будет всё равно рефакторить нормально
"""

import os
import json
import pickle
import shutil
from random import randint
from tempfile import mkstemp
from config import CONFIG, CURRENT_UNIXTIME
from log import log


class DnsDB(object):
    """ Сюда намешана и сама база и методы работы с её содержимым.
    Плохо, но немного лучше чем было до этого """

    def __init__(self, db_file=CONFIG['CACHEFILE'], proto='json'):
        self.file = db_file
        self.queued_count = 0
        self.queued_count_total = 0
        self.data = {}
        if proto == 'json':
            self.read()
        elif proto == 'pickle':
            self.read_bin(db_file)

    def read(self):
        """ читает дикт в память из файла """
        if not os.path.isfile(self.file):
            self.save()
        try:
            _ = json.load(open(self.file))
        except ValueError:
            self.save()
        self.data = json.load(open(self.file)) or {}

    def read_bin(self, filepath):
        """ читает дикт в память из pickle-файла """
        with open(filepath) as output:
            self.data = pickle.load(output)

    def save(self):
        """ save resolved domains into json-file """
        _, fpath = mkstemp(prefix='/tmp/https_resolv.json.')
        with open(fpath, 'w') as tmpfile:
            json.dump(self.data, tmpfile, indent=4)
        shutil.copyfile(fpath, self.file)
        os.unlink(fpath)

    def save_bin(self, filepath):
        """ save resolved domains into pickle dump """
        with open(filepath, 'w') as output:
            pickle.dump(self.data, output)

    @staticmethod
    def eval_ttl(dirty, ttl):
        """decrease if changed else increase MIN_TTL<ttl<MAX_TTL"""
        if ttl == CONFIG['NXDOMAIN_TTL']:
            return dirty and CONFIG['MAX_TTL'] or CONFIG['NXDOMAIN_TTL']
        return min(
            max(
                ttl + (dirty and -10 or randint(1, 5)),
                CONFIG['MIN_TTL']
            ),
            CONFIG['MAX_TTL']
        )

    def receive(self, result):
        """ Callback для QDNS, возвращает name с запросом и ответом """
        self.queued_count -= 1
        if result:
            name, ip_list, ip6_list = result
            self.entry_update(name, ip_list, ip6_list)

    @staticmethod
    def process_ip_lists(entry, ip_list, ip6_list):
        """заполняет списки для записи и возвращает флаг изменились ли они или нет"""
        last_update = CURRENT_UNIXTIME()
        dirty = False
        log.debug("input: ipv4: %s, ipv6: %s", ip_list, ip6_list)
        for version in ('ipv4', 'ipv6'):
            log.debug("process %s", version)
            if version == 'ipv4':
                received = [ipv4 for ipv4 in ip_list if ipv4 not in CONFIG['BLACKHOLES']]
                out = entry.get('ip', {})
            elif version == 'ipv6':
                received = ip6_list
                out = entry.get('ip6', {})
            log.debug("in: %s, out: %s", received, out)
            out_len = len(out)
            for ip in received:
                out[ip] = (CONFIG['IP_TTL'], last_update)
            if out_len != len(out):
                log.debug('dirty cause changed len')
                dirty = True
            for ip, val in out.items():
                if val[1] + val[0] * 60 >= last_update:
                    continue
                log.info('delete %s', ip)
                del out[ip]
                dirty = True
                log.debug('dirty cause del item')
        return dirty, last_update

    # pylint: disable=W0102, R0913
    def entry_add(self, domain, ip={}, ip6={}, last_update=0, ttl=5):
        """ добавляет новую запись (обычно пустую) """
        self.data[domain] = {"ip": ip, "ip6": ip6, "last_update": last_update, "ttl": ttl}

    def entry_del(self, domain):
        """ удаляет лишние записи из базы, чтобы не пухла так быстро """
        if self.data.get(domain):
            del self.data[domain]

    def entry_mark_bad(self, domain, entry=None):
        """ домены которые не зарегистрированы должны резолвиться реже """
        entry = entry or self.data.get(domain)
        if not entry:
            return
        log.info("unresolved %s ttl %d->%d", domain, entry.get('ttl'), CONFIG['NXDOMAIN_TTL'])
        self.entry_update(domain, [], [], CONFIG['NXDOMAIN_TTL'])

    def entry_update(self, domain, ip, ip6, ttl=None):
        """ Вставляем в dict новый dict о домене """
        domain = domain.lower()
        entry = self.data.get(domain)
        if not entry:
            return

        ttl = ttl or entry.get('ttl', 5)
        ip.sort()
        ip6.sort()
        dirty, last_update = self.process_ip_lists(entry, ip, ip6)
        ttl = self.eval_ttl(dirty, ttl)
        if dirty:
            log.info("updated: %s (%d/%d remains)", domain.encode('utf-8'),
                     self.queued_count, self.queued_count_total)
        else:
            log.debug("not changed: %s (%d/%d remains)",
                      domain.encode('utf-8'), self.queued_count, self.queued_count_total)

        self.data[domain] = {
            "ip": entry.get('ip', {}),
            "ip6": entry.get('ip6', {}),
            "last_update": last_update,
            "ttl": ttl,
        }
        log.debug("%s: %s", domain, self.data[domain])


def convert(src, dst):
    """ read json-db and save data in pickle format """
    DnsDB(src, 'json').save_bin(dst)

if __name__ == '__main__':
    convert(CONFIG['CACHEFILE'], CONFIG['CACHEFILE_HOT'])
