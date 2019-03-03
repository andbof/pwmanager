#!/usr/bin/python3

from pwmanager.debug import debug
import fcntl
import os

class GlobalLock():
    def __init__(self, path):
        self.path = os.path.join(path, 'lock')

    def __enter__(self):
        debug('Locking datastore at {}'.format(os.path.dirname(self.path)))
        try:
            f = open(self.path, 'x')
        except FileExistsError:
            f = open(self.path, 'r')
        fcntl.flock(f, fcntl.LOCK_EX)
        self.f = f

    def __exit__(self, type, value, tb):
        debug('Unlocking datastore at {}'.format(os.path.dirname(self.path)))
        # We can never remove the lock file or we might trigger a lock race
        self.f.close()
