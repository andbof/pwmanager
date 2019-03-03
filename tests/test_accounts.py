#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pwmanager.accounts import Accounts
import unittest

class TestAccounts(unittest.TestCase):
    def test_add_rm(self):
        pwds = Accounts()
        self.assertFalse(pwds.exists('host', 'user'))
        pwds.add('host', 'user', 'pwd')
        self.assertTrue(pwds.exists('host', 'user'))
        pwds.rm('host', 'user')
        self.assertFalse(pwds.exists('host', 'user'))

    def test_add_twice(self):
        pwds = Accounts()
        pwds.add('a', 'b', 'c')
        with self.assertRaises(KeyError):
            pwds.add('a', 'b', 'c')
        with self.assertRaises(KeyError):
            pwds.add('a', 'b', 'd')

        pwds.rm('a', 'b')
        pwds.add('a', 'b', 'c')
        with self.assertRaises(KeyError):
            pwds.add('a', 'b', 'c')

    def test_rm_nonexisting(self):
        pwds = Accounts()
        with self.assertRaises(KeyError):
            pwds.rm('a', 'b')

    def test_rm_twice(self):
        pwds = Accounts()
        with self.assertRaises(KeyError):
            pwds.rm('a', 'b')
        pwds.add('a', 'b', 'c')
        pwds.rm('a', 'b')
        with self.assertRaises(KeyError):
            pwds.rm('a', 'b')

    def test_search_empty(self):
        pwds = Accounts()
        l = pwds.search('host', 'user')
        self.assertEqual(l, [])

    def test_search(self):
        pwds = Accounts()
        pwds.add('host', 'user', 'path1')
        pwds.add('hostx', 'userx', 'path2')
        pwds.add('1host1', '1user1', 'path5')
        pwds.add('1host', '1user', 'path4')
        pwds.add('host1', 'user1', 'path3')
        pwds.add('xhost', 'xuser', 'path6')
        pwds.add('xhostx', 'xuserx', 'path7')
        pwds.add('xhoxstx', 'user', 'path8')
        pwds.add('host', 'usxer', 'path9')
        l = pwds.search('host', 'user')

        # Use assertEqual and not assertItemsEqual here because pwds.search()
        # should return matching hosts and users sorted in alphabetical order
        self.assertEqual(l, [
            ('1host', '1user'),
            ('1host1', '1user1'),
            ('host', 'user'),
            ('host1', 'user1'),
            ('hostx', 'userx'),
            ('xhost', 'xuser'),
            ('xhostx', 'xuserx'),
        ])


if __name__ == '__main__':
    unittest.main()
