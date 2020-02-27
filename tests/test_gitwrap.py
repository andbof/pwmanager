#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pwmanager import debug
from pwmanager.gitwrap import Git, GitTransaction
import shutil
import subprocess
import tempfile
import unittest


class TestGit(unittest.TestCase):
    def setUp(self):
        debug.set_debug(False)
        self.tempdir = tempfile.mkdtemp()
        self.orig_cwd = os.getcwd()
        os.chdir(self.tempdir)
        self.repopath = os.path.join(self.tempdir, "origin")
        Git.create_repo(self.repopath, bare=True)
        self.git = Git(self.repopath)

        self.clone_path = os.path.join(self.tempdir, "clone")
        self.git.clone_to(self.clone_path)
        self.gitclone = Git(self.clone_path)
        self.create_file(os.path.join(self.clone_path, "initial"))
        self.gitclone.add("initial")
        self.gitclone.commit("message")
        self.gitclone.push_master()

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.tempdir)

    def create_file(self, path):
        with open(path, 'xb') as f:
            f.write(os.urandom(1024))

    def test_get_head(self):
        # get_head() validates the output so we only need to make sure no
        # exception is raised when running it. It would be better to have a git
        # repo with a previously known hash here but that's probably overkill.
        self.git.get_head()

    def test_rebase(self):
        new_path = os.path.join(self.tempdir, "new")
        self.git.clone_to(new_path)
        git1 = Git(new_path)
        self.create_file(os.path.join(new_path, "one"))
        git1.add("one")
        git1.commit("message1")
        git1.push_master()
        self.assertTrue(os.path.isfile(os.path.join(new_path, "one")))

        newnew_path = os.path.join(self.tempdir, "newnew")
        self.git.clone_to(newnew_path)
        git2 = Git(newnew_path)
        self.create_file(os.path.join(newnew_path, "two"))
        git2.add("two")
        git2.commit("message2")
        git2.push_master()

        self.assertTrue(os.path.isfile(os.path.join(new_path, "one")))
        self.assertFalse(os.path.isfile(os.path.join(new_path, "two")))
        git1.rebase_origin_master()
        self.assertTrue(os.path.isfile(os.path.join(new_path, "one")))
        self.assertTrue(os.path.isfile(os.path.join(new_path, "two")))

    def test_transaction_success(self):
        fpath = os.path.join(self.clone_path, "one")
        with GitTransaction(self.gitclone):
            self.create_file(fpath)
            self.gitclone.add("one")
            self.gitclone.commit("message1")
            self.assertTrue(os.path.isfile(fpath))
            self.gitclone.push_master()
        self.assertTrue(os.path.isfile(fpath))

        # There should be no tags left since the transaction was successful
        self.assertEqual(self.git.run_git(["tag"]), '')
        self.assertEqual(self.gitclone.run_git(["tag"]), '')

    def test_transaction_fail(self):
        new_path = os.path.join(self.tempdir, "new")
        self.git.clone_to(new_path)
        ngit = Git(new_path, silent=True)

        with self.assertRaises(subprocess.CalledProcessError):
            with GitTransaction(ngit):
                self.create_file(os.path.join(self.clone_path, "one"))
                self.create_file(os.path.join(new_path, "two"))
                self.gitclone.add("one")
                ngit.add("two")
                self.gitclone.commit("message1")
                ngit.commit("message2")

                # gitclone.push_master() should succeed but ngit.push_master() should
                # fail because their histories have diverged. When it fails,
                # the ngit commit should be reset to what it was
                self.assertTrue(os.path.isfile(os.path.join(self.clone_path, "one")))
                self.assertTrue(os.path.isfile(os.path.join(new_path, "two")))
                self.gitclone.push_master()

                self.assertTrue(os.path.isfile(os.path.join(self.clone_path, "one")))
                self.assertTrue(os.path.isfile(os.path.join(new_path, "two")))
                ngit.push_master()

                # This line should never be execued as git2.push_master()
                # should break the with block
                self.assertTrue(False)

        self.assertTrue(os.path.isfile(os.path.join(self.clone_path, "one")))
        self.assertFalse(os.path.isfile(os.path.join(new_path, "two")))

        # There should be no tags left since the transaction was aborted
        self.assertEqual(self.git.run_git(["tag"]), '')
        self.assertEqual(self.gitclone.run_git(["tag"]), '')

    def test_has_origin(self):
        self.assertFalse(self.git.has_origin())
        self.assertTrue(self.gitclone.has_origin())


if __name__ == '__main__':
    unittest.main()
