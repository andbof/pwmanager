#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import configparser
import copy
import importlib
from pwmanager.gpgwrap import GPG
from pwmanager import pwmanager
import shutil
import subprocess
import tempfile
from tests.testkey import testkey
import unittest


class Namespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def update(self, **kwargs):
        self.__dict__.update(kwargs)


class TestManage(unittest.TestCase):
    @staticmethod
    def setUp_with_cm(tc, cm):
        enter = cm.__enter__()
        tc.addCleanup(cm.__exit__, None, None, None)
        return enter

    def setUp(self):
        # Reimport the tested module just to ensure nothing is left
        # behind from some older testcase
        importlib.reload(pwmanager)

        self.tempdir = tempfile.mkdtemp()
        self.repodir = os.path.join(self.tempdir, 'origin')
        self.datadir = os.path.join(self.tempdir, 'foo')
        # Replace get_all_pubkeys() with our own test function since
        # the former always calls LDAP
        self.old_get_all_pubkeys = pwmanager.get_all_pubkeys
        pwmanager.get_all_pubkeys = self.get_testkey

        self.gpg = TestManage.setUp_with_cm(self, GPG(False, gnupghome=self.tempdir))
        self.gpg.add_recipient(testkey['private'])
        self.gpg.set_passphrase(testkey['passphrase'])
        self.run_proc(["/usr/bin/git", "init", "--bare", self.repodir], '/')
        self.run_proc(["/usr/bin/git", "clone", self.repodir, "foo"],
                self.tempdir)
        self.create_file(os.path.join(self.datadir, "test"))
        self.run_proc(["/usr/bin/git", "add", "test"], self.datadir)
        self.run_proc(["/usr/bin/git", "commit", "test", "-m", "testmsg"],
                self.datadir)
        self.run_proc(["/usr/bin/git", "push", "origin", "master"],
                self.datadir)

        self.def_args = Namespace(
            host='hostname', user='username', password='secret',
            gnupgpass=testkey['passphrase'],
        )
        self.def_config = configparser.ConfigParser()
        self.def_config['global'] = {
                'debug': 'no',
                'datapath': self.datadir,
                'keys': '',
        }
        self.def_config['gnupg'] = {
                'home': self.tempdir,
                'use_agent': False,
        }

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    @staticmethod
    def run_proc(cmdl, cwd):
        subprocess.check_call(cmdl, cwd=cwd, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)

    @staticmethod
    def create_file(path):
        with open(path, 'x') as f:
            f.write('testfile')

    @staticmethod
    def get_testkey(*args, **kwargs):
        return {'test@example.com': [testkey['public']]}

    def ensure_acc_exists(self, password=None):
        if password is None:
            password = self.def_args.password
        self.assertEqual(pwmanager._get_pwds(
                self.def_config['global']['datapath'], self.gpg,
                self.def_args.host, self.def_args.user),
                [(self.def_args.host, self.def_args.user,
                    "{}\n".format(password))]
        )

    def ensure_acc_not_exists(self):
        self.assertEqual(pwmanager._get_pwds(
                self.def_config['global']['datapath'], self.gpg,
                self.def_args.host, self.def_args.user),
                [])

    def test_add(self):
        # This should call pwmanager.add_pw() in the same way as it is called
        # when running "pwmanager.py add"
        pwmanager.add_pw(self.def_config, self.def_args)
        self.ensure_acc_exists()

    def test_add_twice(self):
        self.ensure_acc_not_exists()
        pwmanager.add_pw(self.def_config, self.def_args)
        self.ensure_acc_exists()
        with self.assertRaises(SystemExit):
            pwmanager.add_pw(self.def_config, self.def_args)
        self.ensure_acc_exists()

    def test_rm_nonexisting(self):
        self.ensure_acc_not_exists()
        # The password does not exist so pwmanager.py should exit with an error
        with self.assertRaises(SystemExit):
            pwmanager.rm_pw(self.def_config, self.def_args)
        self.ensure_acc_not_exists()

    def test_rm(self):
        self.ensure_acc_not_exists()
        pwmanager.add_pw(self.def_config, self.def_args)
        self.ensure_acc_exists()
        pwmanager.rm_pw(self.def_config, self.def_args)
        self.ensure_acc_not_exists()
        with self.assertRaises(SystemExit):
            pwmanager.rm_pw(self.def_config, self.def_args)
        self.ensure_acc_not_exists()

    def test_replace(self):
        self.ensure_acc_not_exists()
        pwmanager.add_pw(self.def_config, self.def_args)
        self.ensure_acc_exists()
        new_args = copy.copy(self.def_args)
        new_args.update(password='other')
        pwmanager.add_pw(self.def_config, new_args, True)
        with self.assertRaises(AssertionError):
            # This should fail because the password is different now
            self.ensure_acc_exists()
        self.ensure_acc_exists('other')


    def test_pipe(self):
        self.ensure_acc_not_exists()
        with self.assertRaises(KeyError):
            pwmanager.get_unique_password(self.def_args.host,
                None, self.def_config['global']['datapath'],
                self.def_config['gnupg'].getboolean('use_agent'),
                self.def_config['gnupg']['home'], self.def_args.gnupgpass
            )

        pwmanager.add_pw(self.def_config, self.def_args)
        self.ensure_acc_exists()
        self.assertEqual(pwmanager.get_unique_password(self.def_args.host,
                self.def_args.user, self.def_config['global']['datapath'],
                self.def_config['gnupg'].getboolean('use_agent'),
                self.def_config['gnupg']['home'], self.def_args.gnupgpass
            ), self.def_args.password)

        new_args = copy.copy(self.def_args)
        new_args.update(user='newuser')
        pwmanager.add_pw(self.def_config, new_args)
        with self.assertRaises(RuntimeError):
            pwmanager.get_unique_password(self.def_args.host,
                None, self.def_config['global']['datapath'],
                self.def_config['gnupg'].getboolean('use_agent'),
                self.def_config['gnupg']['home'], self.def_args.gnupgpass
            )


if __name__ == '__main__':
    unittest.main()
