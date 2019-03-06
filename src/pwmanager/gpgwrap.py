#!/usr/bin/python3

import base64
import getpass
import gnupg
import os
from pwmanager.debug import debug
import shutil
import stat
import tempfile

class GPG():
    """
    Provide python-gnupg with a temporary directory for gnupg settings and
    keyring for encryption during the lifetime of the GPG() object. This allows
    importing and using keys without touching the users normal keyring, which
    is useful if the keys come from a third-party service (e.g. LDAP) at
    runtime.

    Decryption may use either the temporary directory or the real user keyring.
    """
    def __init__(self, use_agent, gnupghome=None):
        self.use_agent = use_agent
        self.gnupghome = gnupghome

    def __enter__(self):
        if self.gnupghome is None:
            self.tempdir = tempfile.mkdtemp()
            os.chmod(self.tempdir, stat.S_IRWXU)
            self.gnupghome = self.tempdir
        else:
            self.tempdir = None

        self.gpg = gnupg.GPG(gnupghome=self.gnupghome, use_agent=self.use_agent)
        self.gpg.encoding = 'latin-1'
        self.encrypt_to = []
        self.passphrase = None
        return self

    def __exit__(self, type, value, tb):
        if self.tempdir is not None:
            shutil.rmtree(self.tempdir)

    def add_recipient(self, data):
        d = base64.b64decode(data)
        r = self.gpg.import_keys(d)
        if (r.count != 1):
            raise RuntimeError("Key import failed")
        self.encrypt_to.append(r.fingerprints[0])

    def encrypt(self, data):
        if not self.encrypt_to:
            raise RuntimeError("No recipients to encrypt to!")
        r = self.gpg.encrypt(data, self.encrypt_to, always_trust=True, armor=True)
        if not r.ok:
            raise RuntimeError("Encryption failed ({})".format(r.status))
        return str(r).encode('latin-1')

    def set_passphrase(self, pw=None):
        if pw is None:
            pw = getpass.getpass('Enter GPG password:')
        else:
            debug('Passphrase already supplied')
        self.passphrase = pw

    def decrypt(self, data):
        debug('Decrypting using gnupg homedir {}'.format(self.gnupghome))
        if not self.use_agent:
            if self.passphrase is None:
                raise RuntimeError("No GPG password set")
            r = self.gpg.decrypt(data, passphrase=self.passphrase)
        else:
            r = self.gpg.decrypt(data)

        if not r.ok:
            raise RuntimeError("Decryption failed ({})".format(r.status))
        return str(r)

    def decrypt_file(self, path):
        debug('Trying to decrypt file {}'.format(path))
        with open(path, 'rb') as f:
            data = f.read()
        return self.decrypt(data)

    def find_key(self, fp):
        for key in self.gpg.list_keys():
            if key['fingerprint'] == fp:
                return key
        return None
