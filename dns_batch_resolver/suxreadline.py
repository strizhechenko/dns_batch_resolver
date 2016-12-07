import sys


def suxreadline(fname=sys.stdin):
    """ Stripping Unicoding Xreadlines from stdin """
    return (unicode(l, 'utf-8').encode('idna') for l in (i.strip() for i in fname.xreadlines()) if l)
