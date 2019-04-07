#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import fcntl
from pwmanager.globallock import GlobalLock
import shutil
import tempfile
import unittest


class TestGlobalLock(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_lock_unlock(self):
        with GlobalLock(self.tempdir):
            pass

    def test_twice(self):
        with GlobalLock(self.tempdir):
            pass
        with GlobalLock(self.tempdir):
            pass

    def test_locked(self):
        def try_lock():
            f = open(os.path.join(self.tempdir, 'lock'), 'r')
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                f.close()

        with GlobalLock(self.tempdir):
            with self.assertRaises(BlockingIOError):
                try_lock()
        try_lock()


if __name__ == '__main__':
    unittest.main()
