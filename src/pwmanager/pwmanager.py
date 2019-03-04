#!/usr/bin/python3

import argparse
import base64
import errno
import getpass
from pwmanager.accounts import Accounts
from pwmanager import config
from pwmanager.debug import debug, set_debug
from pwmanager.gitwrap import Git, GitTransaction
from pwmanager.globallock import GlobalLock
from pwmanager.gpgwrap import GPG
from pwmanager.ldapwrap import get_ldap_group_keys
import os
import sys
import time



def get_version():
    return '{} {}'.format(os.path.basename(sys.argv[0]), '0.1')


def print_sample(cfg, args):
    config.print_sample()


def get_pw_path(fqdn, username):
    return os.path.join(fqdn, username)


def path_to_hostuser(root, fil):
    host = os.path.basename(os.path.normpath(root))
    user = fil.replace('.gpg', '')
    return (host, user)


def hostuser_to_path(root, host, user):
    return '{}.gpg'.format(os.path.join(root,
        os.path.join(host, user)))


def fqdn_user_to_account(fqdn, user):
    return os.path.join(fqdn, user)


def get_all_passwords(datapath):
    accounts = Accounts()
    for root, _, files in os.walk(datapath):
        for fil in files:
            if fil.endswith('.gpg'):
                (host, user) = path_to_hostuser(root, fil)
                accounts.add(host, user, os.path.join(root, fil))
    return accounts


def get_all_pubkeys(cfg):
    """
    Return dict {"email": ["public key in PEM format",...]}
    """

    r = {}

    if 'keys' in cfg['global']:
        with GPG(gnupghome=cfg['gnupg']['home'],
                use_agent=cfg['gnupg'].getboolean('use_agent')) as gpg:
            for fp in cfg['global']['keys'].split(','):
                debug('Fetching public key with fingerprint {} (from configuration file)'.format(fp))
                key_dict = gpg.gpg.list_keys(fp)
                if len(key_dict) != 1:
                    sys.exit('Key with fingerprint {} not found'.format(fp))

                uid = key_dict[0]['uids'][0]
                key_data = gpg.gpg.export_keys(fp)
                if not uid in r:
                    r[uid] = []
                r[uid].append(base64.b64encode(key_data.encode('utf-8')))

    if 'ldap' in cfg:
        debug('Fetching public keys from LDAP')
        try:
            r.update(get_ldap_group_keys(cfg,
                cfg['ldap'].get('bind_pw',
                    getpass.getpass(prompt='LDAP password:')))
            )
        except RuntimeError as e:
            sys.exit(str(e))

    return r


def write_password(path, data, exist_ok):
    mode = 'wb' if exist_ok else 'xb'
    try:
        with open(path, mode) as f:
            f.write(data)
    except FileExistsError:
        sys.exit('{} already exists, bailing out.'.format(path))


def attempt_retry(fnc, *args, **kwargs):
    # This is useful because e.g. some git transactions will fail if multiple
    # people are committing and rebasing simultaneously. Retrying them a few
    # times make sense.
    attempt = 0
    max_attempts = 5
    while True:
        attempt += 1
        debug('Attempting {}, attempt {}/{}'.format(getattr(fnc, '__name__'),
            attempt, max_attempts))
        try:
            return fnc(*args, **kwargs)
        except Exception as e:
            debug('Attempt failed, caught {}: {}'.format(type(e), str(e)))
            if attempt >= 5:
                raise
            time.sleep(0.5)


def add_pw(cfg, args, exist_ok=False):
    def do_add(path, host, user, encpw, exist_ok):
        git = Git(cfg['global']['datapath'])
        with GitTransaction(git):
            if git.has_origin():
                git.rebase_origin_master()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            write_password(path, encpw, exist_ok)
            git.add(path)
            git.commit("{}/{}: {}\n\n{}".format(
                host, user, 'replace' if exist_ok else 'add',
                get_version()))
            if git.has_origin():
                git.push_master()

    accounts = get_all_passwords(cfg['global']['datapath'])

    if not exist_ok and accounts.exists(args.host, args.user):
        sys.exit("Account {} on {} already exists, use replace instead.".format(
            args.user, args.host))

    email_keys = get_all_pubkeys(cfg)

    if args.password is None:
        new_pass = getpass.getpass('Enter password to store:')
        if getpass.getpass('Enter it again to verify:') != new_pass:
            sys.exit("Passwords don't match.")
    else:
        new_pass = args.password

    # We are only encrypting and using different keyrings, so do not use the
    # users gpg-agent even if we were instructed to do so.
    with GPG(use_agent=False) as gpg:
        for email, keys in email_keys.items():
            debug('Encrypting to {} ({} key{})'.format(
                email, len(keys), 's' if len(keys) > 1 else ''))
            for key in keys:
                gpg.add_recipient(key)

        # Adding a trailing newline makes it prettier if someone decodes using
        # regular command line gnupg.
        encpw = gpg.encrypt('{}\n'.format(new_pass))

    path = hostuser_to_path(cfg['global']['datapath'], args.host, args.user)
    attempt_retry(do_add, path, args.host, args.user, encpw, exist_ok)

    print("Successfully encrypted password for {}/{} to {} recipient{}.".format(
        args.host, args.user, len(email_keys), 's' if len(keys) > 1 else ''))


def _get_pwds(cfg, gpg, host, user, gnupgpass):
    accounts = get_all_passwords(cfg['global']['datapath'])
    matches = accounts.search(host, user)
    if not matches:
        return []

    if not cfg['gnupg'].getboolean('use_agent'):
        # gpg-agent should automatically popup a different password dialog so
        # we should only ask for the password if we're not using it
        gpg.set_passphrase(gnupgpass)

    r = []
    for h, u in matches:
        try:
            r.append((h, u, gpg.decrypt_file(accounts.get(h, u),
                cfg['gnupg']['home'], cfg['gnupg'].getboolean('use_agent'))))
        except RuntimeError:
            sys.exit('Decryption failed. Check password and availability of secret key.')
    return r


def get_pwds(cfg, host, user, gnupgpass):
    with GPG(gnupghome=cfg['gnupg']['home'],
            use_agent=cfg['gnupg'].getboolean('use_agent')) as gpg:
        return _get_pwds(cfg, gpg, host, user, gnupgpass)


def get_pw(cfg, args):
    def print_row(a, b, c):
        print('{:20s} {:16s} {:20s}'.format(a, b, c))

    pwds = get_pwds(cfg, args.host, args.user, args.gnupgpass)
    if not pwds:
        print("No matches for host '{}' {}".format(args.host,
            "and user '{}'".format(args.user) if args.user is not None else ''))
    else:
        print("{} match{} for host '{}' {}:\n".format(
            len(pwds), 'es' if len(pwds) > 1 else '', args.host,
            "and user '{}'".format(args.user) if args.user is not None else '(all users)'))

        print_row('Host', 'User', 'Password')
        print_row('----', '----', '--------')
        for x in pwds:
            # Passwords are stored with a trailing newline to make decryption
            # using command line gpg easier
            print_row(x[0], x[1], x[2].rstrip())


def rm_pw(cfg, args):
    def do_rm(pwfile, host, user):
        git = Git(cfg['global']['datapath'])
        with GitTransaction(git):
            if git.has_origin():
                git.rebase_origin_master()
            git.rm(pwfile)
            git.commit("{}/{}: remove\n\n{}".format(
                args.host, args.user, get_version()))
            if git.has_origin():
                git.push_master()

    accounts = get_all_passwords(cfg['global']['datapath'])
    if not accounts.exists(args.host, args.user):
        sys.exit("User {} on args.host {} does not exist".format(args.user, args.host))

    debug("Removing password for account '{}/{}'".format(args.host, args.user))

    pwfile = accounts.get(args.host, args.user)
    attempt_retry(do_rm, pwfile, args.host, args.user)
    try:
        os.rmdir(os.path.dirname(pwfile))
    except OSError as e:
        if e.errno == errno.ENOTEMPTY:
            debug("More accounts exist for '{}', not removing args.host".format(args.host))
    else:
        debug("No more accounts exist for '{}', args.host removed".format(args.host))

    print("Password for user {} on host {} removed".format(args.user, args.host))


def replace_pw(cfg, args):
    return add_pw(cfg, args, exist_ok=True)


def list_same(a, b):
    if set(a) - set(b):
        return False
    if set(b) - set(a):
        return False
    return True


def sync(cfg, host, user, _):
    sys.exit('Not implemented yet')


def init_git(cfg, args):
    datapath = cfg['global']['datapath']
    if os.path.isdir(os.path.join(datapath, ".git")):
        sys.exit('{} is already a git repo! Not reinitializing to avoid losing data.'.format(
            datapath))

    os.makedirs(datapath, exist_ok=True)
    Git.create_repo(datapath, bare=False)
    fn = os.path.join(datapath, '.gitignore')
    with open(fn, 'x') as f:
        f.write('lock\n')
    git = Git(datapath)
    git.add('.gitignore')
    git.commit('Initial')
    print('Password storage git repo initialized in {}'.format(datapath))


HOST_ARG = {
    'action': 'store',
    'help': "Host where the password is valid (e.g. 'host.company.com')",
    'nargs': None,
    'type': str.lower,
    'metavar': 'HOSTFQDN',
    'default': None,
}

USER_ARG = {
    'action': 'store',
    'help': "Username for which the password is valid (e.g. 'root')",
    'nargs': None,
    'type': str.lower,
    'metavar': 'USER',
    'default': None,
}

PWD_ARG = {
    'action': 'store',
    'help': 'Password to store (will be prompted for, if omitted)',
    'nargs': '?',
    'type': str,
    'metavar': 'PASSWORD',
    'default': None,
}

actions = {
        'add': {
            'help': 'Add a new password',
            'method': add_pw,
            'pos_args': [
                ('host', HOST_ARG),
                ('user', USER_ARG),
                ('password', PWD_ARG),
            ],
            'opt_args': {},
        },
        'get': {
            'help': 'Get password for accounts matching host (and user) as substrings',
            'method': get_pw,
            'pos_args': [
                ('host', HOST_ARG),
                ('user', {
                    'action': 'store',
                    'nargs': '?',
                    'type': str.lower,
                    'metavar': 'USER',
                    'help': 'Username (if omitted, list all passwords on HOSTFQDN)',
                }),
            ],
            'opt_args': {},
        },
        'replace': {
            'help': 'Replace existing password (the new password may be the same as the old one)',
            'method': replace_pw,
            'pos_args': [
                ('host', HOST_ARG),
                ('user', USER_ARG),
                ('password', PWD_ARG),
            ],
            'opt_args': {},
        },
        'rm': {
            'help': 'Delete a password',
            'method': rm_pw,
            'pos_args': [
                ('host', HOST_ARG),
                ('user', USER_ARG),
            ],
            'opt_args': {},
        },
        'sync': {
            'help': 'Go through all passwords and reencrypt to all configured public key (and noone else)',
            'method': sync,
            'pos_args': [],
            'opt_args': {},
        },
        'init': {
            'help': 'Initialize the datastore git repository',
            'method': init_git,
            'pos_args': [],
            'opt_args': {},
        },
}


def parse_cmdline(actions):
    parser = argparse.ArgumentParser(description=
            'Add or remove keys from a git backed gpg encrypted database',
    )

    parser.add_argument('-c', '--config',
            help='Configuration file (default: {})'.format(config.DEFAULT_CONF),
            action='store', type=str, metavar='PATH', default=config.DEFAULT_CONF)

    parser.add_argument('-d', '--debug',
            help='Turn debugging mode on',
            action='store_true', default=False)

    parser.add_argument('--gnupgpass',
            help='Password to gnupg (will be prompted for if omitted)',
            action='store', type=str, metavar='PASSWORD', default=None)

    parser.add_argument('-s', '--datapath',
            help="Path to key data store directory (default: '{}' subdir)".format(
                config.DEFAULT_DATA_DIR),
            action='store', type=str, metavar='PATH', default=config.DEFAULT_DATA_DIR)

    parser.add_argument('-V', '--version',
            help='Display version and exit',
            action='version', version=get_version())

    subp = parser.add_subparsers(dest='action')
    for name, val in sorted(actions.items()):
        p = subp.add_parser(name, help=val['help'])
        for arg in val['pos_args']:
            p.add_argument(arg[0],
                    action=arg[1]['action'], help=arg[1]['help'],
                    nargs=arg[1]['nargs'],
                    type=arg[1]['type'], metavar=arg[1]['metavar'])
        for _name, _val in sorted(val['opt_args'].items()):
            p.add_argument(_name, _val['long'],
                    action=_val['action'], help=_val['help'],
                    type=_val['type'], metavar=_val['metavar'])

    args = parser.parse_args()
    if args.action is None:
        parser.print_help()
        # ArgumentParser() exits with error 2 if action is invalid, so let's
        # use the same value here
        sys.exit(2)

    return args


def validate(s):
    for x in s:
        if not x.isprintable():
            return False
        if x.isspace():
            return False
        if x == '/':
            return False
    return True


def main():
    args = parse_cmdline(actions)
    set_debug(args.debug)

    if not os.path.exists(args.config):
        sys.exit(
                'No configuration file {}\n'.format(args.config) + \
                'Please install and edit pwmanager.conf.sample'
        )

    cfg = config.parse(args.config)

    if args.datapath is not None:
        cfg['global']['datapath'] = args.datapath
    if args.debug:
        cfg['global']['debug'] = 'yes'
    set_debug(True if cfg['global'].getboolean('debug') else False)

    if not os.path.exists(cfg['global']['datapath']):
        sys.exit('{} does not exist!'.format(cfg['global']['datapath']))

    if 'host' in args and args.host is not None and not validate(args.host):
        sys.exit("'{}' is not a valid hostname".format(args.host))
    if 'user' in args and args.user is not None and not validate(args.user):
        sys.exit("'{}' is not a valid username".format(args.user))

    with GlobalLock(args.datapath):
        return actions[args.action]['method'](cfg, args)


if __name__ == '__main__':
    main()
