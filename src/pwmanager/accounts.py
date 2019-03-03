#!/usr/bin/python3

class Accounts():
    def __init__(self):
        """
        self.accounts is a dict of a dict mapping hosts and users to file paths on
        disk where the password is stored:
        {
            'host.domain': {
                'user1': 'path/password.gpg',
                'user2': 'path/password.gpg',
            },
            'x.domain': {
                ...
            },
            ...
        }
        """
        self.accounts = {}

    def add(self, host, user, path):
        if not host in self.accounts:
            self.accounts[host] = {}
        if user in self.accounts[host]:
            raise KeyError('Adding user {} on host {} twice'.format(user, host))
        self.accounts[host][user] = path

    def exists(self, host, user):
        if not host in self.accounts:
            return False
        if not user in self.accounts[host]:
            return False
        return True

    def rm(self, host, user):
        if not self.exists(host, user):
            raise KeyError('Trying to remove non-existing user {} on host {}'.format(
                user, host))
        del(self.accounts[host][user])
        if not self.accounts[host]:
            del(self.accounts[host])

    def get(self, host, user):
        if not self.exists(host, user):
            raise KeyError('Trying to remove non-existing user {} on host {}'.format(
                user, host))
        return self.accounts[host][user]

    def search(self, h, u):
        r = []
        for host, users in sorted(self.accounts.items()):
            if h is not None and not h in host:
                continue
            for user in sorted(users):
                if u is not None and not u in user:
                    continue
                r.append((host, user))
        return r
