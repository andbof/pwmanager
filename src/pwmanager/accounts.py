#!/usr/bin/python3

class Accounts():
    def __init__(self):
        """
        self.accounts is a dict of a dict mapping hosts and users to file paths on
        disk where the password is stored:
        {
            'host.domain': {
                'user1': {
                    'raw_host': "Host",
                    'raw_user': "UsEr1",
                    'path': 'path/password.gpg',
                },
                'user2': { ... },
            },
            'x.domain': {
                ...
            },
            ...
        }
        """
        self.accounts = {}

    def add(self, host, user, path):
        _host = host.lower()
        _user = user.lower()
        if not _host in self.accounts:
            self.accounts[_host] = {}
        if _user in self.accounts[_host]:
            raise KeyError('Adding user {} on host {} twice'.format(_user, _host))
        self.accounts[_host][_user] = {
                'raw_host': host,
                'raw_user': user,
                'path': path,
        }

    def exists(self, host, user):
        _host = host.lower()
        _user = user.lower()
        if not _host in self.accounts:
            return False
        if not _user in self.accounts[_host]:
            return False
        return True

    def rm(self, host, user):
        _host = host.lower()
        _user = user.lower()
        if not self.exists(_host, _user):
            raise KeyError('Trying to remove non-existing user {} on host {}'.format(
                _user, _host))
        del(self.accounts[_host][_user])
        if not self.accounts[_host]:
            del(self.accounts[_host])

    def get(self, host, user):
        _host = host.lower()
        _user = user.lower()
        if not self.exists(_host, _user):
            raise KeyError('Trying to remove non-existing user {} on host {}'.format(
                _user, _host))

        acc = self.accounts[_host][_user]
        return (acc['raw_host'], acc['raw_user'], acc['path'])

    def search(self, h, u):
        """
        Returns the hosts and users matching the two search strings h and u,
        respectively. Will return the lowercased versions of host and user, not
        the real ones.
        """
        _h = h.lower() if h is not None else None
        _u = u.lower() if u is not None else None
        r = []
        for host, users in sorted(self.accounts.items()):
            if _h is not None and not _h in host:
                continue
            for user in sorted(users):
                if _u is not None and not _u in user:
                    continue
                r.append((host, user))
        return r

    def iterate(self):
        for host, users in self.accounts.items():
            for user, val in users.items():
                yield (val['raw_host'], val['raw_user'], val['path'])
