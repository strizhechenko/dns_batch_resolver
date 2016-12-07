#!/usr/bin/env python
# coding: utf-8
""" Обновляет устаревшие записи в кэше DNS """

import os
import logging
import qdns
from db import DnsDB
from config import CONFIG, CURRENT_UNIXTIME
from suxreadline import suxreadline

__author__ = 'Oleg Strizhechenko <oleg@carbonsoft.ru>'


def is_out_date(entry, cur_time):
    """ Проверяем, устарели ли данные о домене и насколько """
    if not (entry.get('ttl') and entry.get('last_update')):
        return True
    if entry.get('ttl') * 60 + entry.get('last_update') < cur_time:
        return True
    out_of_date = any(
        [ip[1] + ip[0] * 60 < cur_time for ip in entry.get('ip').values()])
    return out_of_date


def queue_normal(db):
    """ Прогоняем все домены резолвером """
    qdns_configured = False
    current_time = CURRENT_UNIXTIME()
    logging.info('queue outdated domains')
    db.queued_count = 0
    for domain, entry in db.data.items():
        if domain not in DOMAINS:
            continue
        if not is_out_date(entry, current_time):
            continue
        if not qdns_configured:
            logging.info('qdns.configure')
            cpu_count = int(os.environ.get('QDNS_THREADS', 4))
            qdns.configure(new_thread_count=cpu_count,
                           carbon=True, __ipv6_support=CONFIG['IPV6_SUPPORT'])
            qdns_configured = True
        db.queued_count += 1
        logging.info("queued: %s", domain.encode('utf-8'))
        qdns.gethostsbyname(domain, db.receive)
        DOMAINS_QUEUED.append(domain)
        # отрицательный RESOLVER_LIMIT == резолвить всё
        if CONFIG['RESOLVER_LIMIT'] < 0:
            continue
        # не резолвим всё, только в пределах лимита, чтобы резолвер не висел долго
        if CONFIG['RESOLVER_LIMIT'] <= db.queued_count:
            logging.info('check only first %d domains', CONFIG['RESOLVER_LIMIT'])
            break
    db.queued_count_total = int(db.queued_count)
    logging.info("total queued: %d", db.queued_count_total)
    if qdns_configured:
        qdns.stop(True)
        logging.info('qdns stopped')


def set_as_bad(db):
    """ Помечаем домены, по которым не получили ответ от DNS сервера плохими """
    logging.info('mark unresolved domains')
    current_time = CURRENT_UNIXTIME()
    for domain, entry in db.data.items():
        if domain not in DOMAINS_QUEUED:
            continue
        out_of_date = is_out_date(entry, current_time)
        empty = not entry.get('ip') and not entry.get('ip6')
        marked_as_bad = entry.get('ttl') == CONFIG['NXDOMAIN_TTL']
        if out_of_date or (empty and not marked_as_bad):
            db.entry_mark_bad(domain)


def remove_blackhole_ip(db):
    """remove blackholes ip addresses from resolv cache"""
    logging.info("%s", remove_blackhole_ip.__doc__)
    for domain, value in db.data.items():
        for blackhole in CONFIG['BLACKHOLES']:
            if value.get('ip').get(blackhole):
                logging.info('remove %s from %s', blackhole, domain)
                del value.get('ip')[blackhole]


def resolv():
    logging.info('start')
    # pylint: disable=W0603
    global DOMAINS
    DOMAINS = set(list(suxreadline()))
    if not DOMAINS:
        logging.info("No domains to process, skip")
        exit(0)
    db = DnsDB()
    queue_normal(db)
    set_as_bad(db)
    remove_blackhole_ip(db)
    db.save()
    logging.info('finished')

if __name__ == '__main__':
    DOMAINS_QUEUED = []
    DOMAINS = set()
    resolv()
