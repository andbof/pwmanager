#!/usr/bin/python3

from pwmanager.debug import debug
import subprocess
import sys
import uuid

class Git():
    def __init__(self, repo, git="/usr/bin/git", silent=False):
        self.repo_path = repo
        self.git = git
        self.silent = silent

    def run_git(self, cmdl):
        cmdl.insert(0, self.git)
        stdout = []
        stderr = []
        debug("Running '{}' in {}".format(' '.join(cmdl).replace('\n', '\\n'),
            self.repo_path))
        p = subprocess.Popen(cmdl, cwd=self.repo_path,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            (stdout, stderr) = p.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            sys.exit("git commandline '{}' timed out".format(cmdl))
        output = '{}{}'.format(
                stdout.decode('utf-8') if stdout else '',
                stderr.decode('utf-8') if stderr else ''
        )
        if p.returncode != 0:
            if not self.silent:
                print(output)
            raise subprocess.CalledProcessError(cmd=cmdl,
                    returncode=p.returncode, output=output)

        # The output from git tends to be very verbose so we make it a bit
        # more dense here from debugging purposes.
        debug('git returned success: {}'.format(
            '(no output)' if not output else ''))
        for line in output.split('\n'):
            if line == '' or line.isspace():
                continue
            debug('    {}'.format(line))

        return output

    @staticmethod
    def create_repo(path, bare=False):
        # This must be a static method since the Git() class requires (for
        # convenience) a path to an existing git repo, and for obvious reasons
        # thers is none when running this method.
        git = Git("/")
        if not bare:
            cmdl = ["init", path]
        else:
            cmdl = ["init", "--bare", path]
        git.run_git(cmdl)

    def clone_to(self, path):
        self.run_git(["clone", ".", path])

    def add(self, path):
        self.run_git(["add", path])

    def rm(self, path):
        self.run_git(["rm", path])

    def tag(self, name):
        self.run_git(["tag", name])

    def rm_tag(self, name):
        self.run_git(["tag", "-d", name])

    def commit(self, msg):
        self.run_git(["commit", "-m", msg])

    def push_master(self):
        self.run_git(["push", "origin", "master"])

    def rebase_origin_master(self):
        self.run_git(["fetch", "origin"])
        self.run_git(["rebase", "origin/master"])

    def has_origin(self):
        out = self.run_git(["remote"])
        return 'origin\n' in out


class GitTransaction():
    def __init__(self, git):
        self.git = git
        self.tag = str(uuid.uuid4())

    def __enter__(self):
        debug('Starting git transaction {}'.format(self.tag))
        self.git.tag(self.tag)

    def rollback(self):
        self.git.run_git(["reset", "--hard", self.tag])
        self.git.run_git(["clean", "-dffx"])

    def __exit__(self, type, value, tb):
        if tb is not None:
            # An exception occured, roll back. The exception will be re-raised
            # once this handler is complete.
            debug('Exception occured, aborting git transaction to saved state')
            self.rollback()
        else:
            debug('Git transaction completed cleanly')
        self.git.rm_tag(self.tag)
