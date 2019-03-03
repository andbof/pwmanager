#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pwmanager.gpgwrap import GPG
import shutil
import tempfile
from tests.testkey import testkey
import unittest

class TestGPG(unittest.TestCase):
    @staticmethod
    def setUp_with_cm(tc, cm):
        enter = cm.__enter__()
        tc.addCleanup(cm.__exit__, None, None, None)
        return enter

    def setUp(self):
        self.gpg = TestGPG.setUp_with_cm(self, GPG(use_agent=False))
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_encrypt_no_recipients(self):
        with self.assertRaises(RuntimeError):
            self.gpg.encrypt('test')

    def test_decrypt_no_key(self):
        data = str(os.urandom(1024))
        self.gpg.add_recipient(testkey['public'])
        blob = self.gpg.encrypt(data)
        with self.assertRaises(RuntimeError):
            self.gpg.decrypt(blob, self.gpg.tempdir, use_agent=False)
        with self.assertRaises(RuntimeError):
            self.gpg.set_passphrase(testkey['passphrase'])
            self.gpg.decrypt(blob, self.gpg.tempdir, use_agent=False)

    def test_encrypt_decrypt(self):
        data = str(os.urandom(1024))
        self.gpg.add_recipient(testkey['private'])
        blob = self.gpg.encrypt(data)
        self.gpg.set_passphrase(testkey['passphrase'])
        out = self.gpg.decrypt(blob, self.gpg.tempdir, use_agent=False)
        self.assertEqual(data, out)

    def test_encrypt_decrypt_file(self):
        data = str(os.urandom(1024))
        self.gpg.add_recipient(testkey['private'])
        blob = self.gpg.encrypt(data)
        path = os.path.join(self.tempdir, 'test.gpg')
        with open(path, 'xb') as f:
            f.write(blob)
        self.gpg.set_passphrase(testkey['passphrase'])
        out = self.gpg.decrypt_file(path, self.gpg.tempdir, use_agent=False)
        self.assertEqual(data, out)


if __name__ == '__main__':
    unittest.main()
