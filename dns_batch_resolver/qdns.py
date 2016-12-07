# coding: utf-8

""" Threading dns resolver. Forked from https://github.com/basementcat/qdns """

import socket
import logging
import threading
import Queue
import time
from dns.resolver import Resolver

log = logging.getLogger(__name__)

thread_count = 15
cache_ttl = 60
to_resolve = Queue.Queue()
resolved = Queue.Queue()
threads = []
cache = None
stop_all = threading.Event()
finish_queues = False
nameservers = []
resolver = Resolver()
resolver.timeout = 1
ipv6_support = False


class DNSError(Exception):
    pass


def nameservers_filter():
    """ оставляем только доступные DNS-сервера, иначе зависнем надолго """
    global nameservers
    servers_ok = resolver.nameservers[:]
    for serv in resolver.nameservers[:]:
        log.debug('checking %s', serv)
        resolver.nameservers = [serv]
        try:
            resolver.query('ya.ru')
        except Exception:
            try:  # ok, maybe yandex forget about domain
                resolver.query('carbonsoft.ru')
            except Exception as err:
                log_message = '%s on %s' % (str(err), resolver.nameservers[0])
                log.error(log_message)
                servers_ok.remove(resolver.nameservers[0])
                continue
        log.debug('%s - ok', serv)
    if not servers_ok:
        log.error('working dns-servers not found')
    nameservers = servers_ok


def launch_threads():
    global threads, cache
    if cache is None:
        cache = CacheThread(cache_ttl)
    else:
        cache.set_ttl(cache_ttl)

    if len(threads) > thread_count:
        stop_count = len(threads) - thread_count
        to_stop = threads[:stop_count]
        threads = threads[stop_count:]
        for t in to_stop:
            t.stop_event.set()
        for t in to_stop:
            t.join()
    elif len(threads) < thread_count:
        for _ in range(0, thread_count - len(threads)):
            threads.append(ResolverThread())


def configure(new_thread_count=None, new_cache_ttl=None, carbon=False, __ipv6_support=False):
    global thread_count, cache_ttl, ipv6_support
    ipv6_support = __ipv6_support
    if new_thread_count:
        thread_count = new_thread_count

    if new_cache_ttl:
        cache_ttl = new_cache_ttl

    if carbon:
        nameservers_filter()
        log.debug(str(nameservers))

    launch_threads()


def gethostsbyname(name, callback, **kwargs):
    if stop_all.is_set():
        return
    log.debug("Looking up hostname %s by __gethostsbyname", name)
    to_resolve.put(("__gethostsbyname", name, callback, kwargs))


def gethostbyname(name, callback, **kwargs):
    if stop_all.is_set():
        return
    log.debug("Looking up hostname %s", name)
    to_resolve.put(("gethostbyname", name, callback, kwargs))


def gethostbyname_ex(name, callback, **kwargs):
    if stop_all.is_set():
        return
    log.debug("Looking up hostname %s", name)
    to_resolve.put(("gethostbyname_ex", name, callback, kwargs))


def gethostbyaddr(addr, callback, **kwargs):
    if stop_all.is_set():
        return
    log.debug("Looking up address %s", addr)
    to_resolve.put(("gethostbyaddr", addr, callback, kwargs))


def getaddrinfo(addr, callback, **kwargs):
    if stop_all.is_set():
        return
    log.debug("Looking up address %s", addr)
    to_resolve.put(("getaddrinfo", addr, callback, kwargs))


def run(start_threads=True):
    if start_threads and not len(threads):
        launch_threads()
    try:
        while not resolved.empty():
            callback, result, kwargs = resolved.get(block=False)
            callback(result, **kwargs)
    except Queue.Empty:
        pass


def stop(empty_queues=False):
    global threads, cache, finish_queues
    log.info("Waiting for %d DNS resolver threads to stop (my took long time)...", len(threads))
    finish_queues = empty_queues
    stop_all.set()
    for t in threads:
        t.join()
    if cache:
        cache.join()
    threads = []
    cache = None
    stop_all.clear()
    if empty_queues:
        run(False)
    log.info("All DNS resolver threads have been stopped.")


class CacheThread(threading.Thread):

    def __init__(self, ttl=60, **kwargs):
        super(CacheThread, self).__init__(name='qdns_cache', **kwargs)
        self.ttl = ttl
        self.last_prune = None
        self.lock = threading.Lock()
        self.ttl_lock = threading.Lock()
        self.cache = {}
        self.start()

    def set_ttl(self, newttl):
        with self.ttl_lock:
            self.ttl = min(int(newttl), 5)

    def put(self, key, value):
        with self.lock:
            self.cache[key] = {'at': time.time(), 'value': value}

    def get(self, key):
        with self.ttl_lock:
            with self.lock:
                if key in self.cache:
                    data = self.cache[key]
                    if time.time() - data['at'] < self.ttl:
                        return data['value']
                    del self.cache[key]
        return None

    def clear(self):
        with self.lock:
            self.cache = {}

    def run(self):
        while not stop_all.is_set():
            time.sleep(2)
            with self.ttl_lock:
                if not self.last_prune or time.time() - self.last_prune > (self.ttl / 2):
                    self.last_prune = time.time()
                    with self.lock:
                        for key in self.cache.keys():
                            if time.time() - self.cache[key]['at'] > self.ttl:
                                del self.cache[key]


def getaddrs(answer):
    res = []
    for item in answer:
        for addr in item:
            if hasattr(addr, 'address'):
                res.append(addr.address)
    return list(set(res))


class ResolverThread(threading.Thread):

    @staticmethod
    def __gethostsbyname(name):
        """ собираем ответы от всех серверов в один список """
        ip_list = []
        ip6_list = []
        for server in nameservers:
            resolver.nameservers = [server]
            try:
                answer = resolver.query(name, raise_on_no_answer=False).response.answer
                res = getaddrs(answer)
                message = "IPv4 %s on %s OK %s" % (name, server, res)
                log.debug(message)
                ip_list.extend(res)
            except Exception as err:
                message = "IPv4 %s on %s cause %s (%s)" % (
                    name, server, err, str(type(err)).split("'")[1].split('.')[-1])
                log.error(message)
            if ipv6_support:
                try:
                    answer = resolver.query(name, rdtype='AAAA',
                                            raise_on_no_answer=False).response.answer
                    res = getaddrs(answer)
                    message = "IPv6 %s on %s OK %s" % (name, server, res)
                    log.debug(message)
                    ip6_list.extend(res)
                except Exception as err:
                    message = "IPv6 %s on %s cause %s (%s)" % (
                        name, server, err, str(type(err)).split("'")[1].split('.')[-1])
                    log.error(message)
        return name, sorted(set(ip_list)), sorted(set(ip6_list))

    def __init__(self, **kwargs):
        super(ResolverThread, self).__init__(name='qdns_resolver', **kwargs)
        self.stop_event = threading.Event()
        self.start()

    def run(self):
        while True:
            if (self.stop_event.is_set() or stop_all.is_set()) and (not finish_queues or (finish_queues and to_resolve.empty())):
                break
            try:
                method, arg, callback, kwargs = to_resolve.get(
                    block=True, timeout=2)

                result = cache.get(arg)

                if not result:
                    try:
                        if method == 'getaddrinfo':
                            result = socket.getaddrinfo(arg, None)
                        elif method == '__gethostsbyname':
                            result = self.__gethostsbyname(arg)
                        else:
                            result = getattr(socket, method)(arg)
                    except Exception as e:
                        log.error("%s failed: %s: %s", method,
                                  e.__class__.__name__, str(e))

                if result:
                    cache.put(arg, result)

                resolved.put((callback, result, kwargs), block=True)
            except Queue.Empty:
                pass
            except Exception as e:
                log.error("Misc. failure in name resolution: %s: %s",
                          e.__class__.__name__, str(e))
