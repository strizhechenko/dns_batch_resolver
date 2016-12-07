# coding: utf-8
""" Тесты базы данных резолвера """
import os
import unittest
from dns_db import DnsDB
from dns_config import NXDOMAIN_TTL, MAX_TTL


class DnsDBTest(unittest.TestCase):
    """ Тесты базы данных резолвера """

    def setUp(self):
        self.db = DnsDB(db_file='/tmp/dns_db_test')

    def tearDown(self):
        os.remove(self.db.file)

    def test_eval_ttl(self):
        """ тесты модификации TTL записи при модификации/неизменности """
        self.assertLess(self.db.eval_ttl(True, 50), 50)
        self.assertGreater(self.db.eval_ttl(False, 50), 50)
        self.assertEqual(self.db.eval_ttl(False, NXDOMAIN_TTL), NXDOMAIN_TTL)
        self.assertEqual(self.db.eval_ttl(True, NXDOMAIN_TTL), MAX_TTL)

    def test_mark_as_bad(self):
        self.db.entry_add("unresolv.ed")
        self.db.entry_mark_bad("unresolv.ed")
        self.assertEqual(self.db.data.get("unresolv.ed").get("ttl"), NXDOMAIN_TTL)

    def test_update_entry(self):
        self.db.entry_add("ok.ok")
        self.db.entry_update("ok.ok", ip=[], ip6=[], ttl=60)
        self.assertEqual(self.db.data.get("ok.ok").get("ttl"), 60)
        self.db.entry_update("ok.ok", ip=[], ip6=[], ttl=50)
        self.assertGreater(self.db.data.get("ok.ok").get("ttl"), 50)
