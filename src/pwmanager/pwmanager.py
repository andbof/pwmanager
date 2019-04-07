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
    return '{} {}'.format(os.path.basename(sys.argv[0]), '1.0')


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


def get_all_pubkeys(fps, ldap, use_agent, gpg_path, gnupghome):
    """
    Return dict {"email": ["public key in PEM format",...]}
    """

    r = {}

    with GPG(use_agent, gpg_path, gnupghome) as gpg:
        for fp in fps:
            debug('Fetching public key with fingerprint {} (from configuration file)'.format(fp))
            key = gpg.find_key(fp)
            if key is None:
                sys.exit('Key with fingerprint {} not found'.format(fp))

            uid = key['uids'][0]
            key_data = gpg.gpg.export_keys(fp)
            if not uid in r:
                r[uid] = []
            r[uid].append(base64.b64encode(key_data.encode('utf-8')))

    if ldap is not None:
        debug('Fetching public keys from LDAP')
        try:
            r.update(get_ldap_group_keys(ldap, ldap.get('bind_pw',
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


def write_and_add(git, path, encpw, exist_ok):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_password(path, encpw, exist_ok)
    git.add(path)


def do_add(datapath, path, host, user, encpw, exist_ok):
    git = Git(datapath)
    with GitTransaction(git):
        if git.has_origin():
            git.rebase_origin_master()
        write_and_add(git, path, encpw, exist_ok)
        git.commit("{}/{}: {}\n\n{}".format(
            host, user, 'replace' if exist_ok else 'add',
            get_version()))
        if git.has_origin():
            git.push_master()


def _add_pw(host, user, password, datapath, keys, exist_ok, gpg_path, gnupghome):
    accounts = get_all_passwords(datapath)

    if not exist_ok and accounts.exists(host, user):
        sys.exit("Account {} on {} already exists, use replace instead.".format(
            user, host))

    if password is None:
        new_pass = getpass.getpass('Enter password to store:')
        if getpass.getpass('Enter it again to verify:') != new_pass:
            sys.exit("Passwords don't match.")
    else:
        new_pass = password

    # We are only encrypting and using different keyrings, so do not use the
    # users gpg-agent even if we were instructed to do so.
    with GPG(False, gpg_path, gnupghome) as gpg:
        for email, fp_list in keys.items():
            debug('Encrypting to {} ({} key{})'.format(
                email, len(fp_list), 's' if len(fp_list) > 1 else ''))
            for fp in fp_list:
                gpg.add_recipient(fp)

        # Adding a trailing newline makes it prettier if someone decodes using
        # regular command line gnupg.
        encpw = gpg.encrypt('{}\n'.format(new_pass))

    path = hostuser_to_path(datapath, host, user)
    attempt_retry(do_add, datapath, path, host, user, encpw, exist_ok)
    return gpg.get_num_recipients()


def get_fps_from_conf(cfg):
    fps = cfg['global']['keys'].split(',')
    # Filter out empty entries (e.g. user has entered 'keys=fp,' or 'keys=' is
    # missing altogether
    return [x for x in fps if x]


def add_pw(cfg, args, exist_ok=False):
    if not 'ldap' in cfg:
        ldap = None
    else:
        ldap = cfg['ldap']

    keys = get_all_pubkeys(get_fps_from_conf(cfg), ldap,
            cfg['gnupg'].getboolean('use_agent'), cfg['gnupg']['home'])

    r = _add_pw(args.host, args.user, args.password, cfg['global']['datapath'],
            keys, exist_ok, cfg['gnupg']['gpg_path'], cfg['gnupg']['home'])
    print("Successfully encrypted password for {}/{} to {} recipient{}.".format(
        args.host, args.user, r, 's' if r > 1 else ''))


def _get_pwds(datapath, gpg, host, user):
    accounts = get_all_passwords(datapath)
    matches = accounts.search(host, user)
    if not matches:
        return []

    r = []
    for h, u in matches:
        try:
            (_h, _u, path) = accounts.get(h, u)
            r.append((_h, _u, gpg.decrypt_file(path)))
        except RuntimeError:
            sys.exit('Decryption failed. Check password and availability of secret key.')
    return r


def get_pwds(host, user, datapath, use_agent, gpg_path, gnupghome, gnupgpass):
    with GPG(use_agent, gpg_path, gnupghome) as gpg:
        if not use_agent:
            # gpg-agent should automatically popup a different password dialog so
            # we should only ask for the password if we're not using it
            gpg.set_passphrase(gnupgpass)

        return _get_pwds(datapath, gpg, host, user)


def print_result(pwds, host, user):
    def find_longest(l):
        m = 0
        for x in l:
            if len(x) > m:
                m = len(x)
        return m

    if not pwds:
        print("No matches for host '{}' {}".format(host,
            "and user '{}'".format(user) if user is not None else ''))
    else:
        print("{} match{} for host '{}' {}:\n".format(
            len(pwds), 'es' if len(pwds) > 1 else '', host,
            "and user '{}'".format(user) if user is not None else '(all users)'))

        pwds.insert(0, ('Host', 'User', 'Password'))
        pwds.insert(1, ('----', '----', '--------'))
        wa = find_longest([x[0] for x in pwds]) + 2
        wb = find_longest([x[1] for x in pwds]) + 2
        wc = find_longest([x[2] for x in pwds]) + 2
        # Passwords are stored with a trailing newline to make decryption
        # using command line gpg easier
        for x in pwds:
            print('{:{}s} {:{}s} {:{}s}'.format(x[0], wa, x[1], wb, x[2].rstrip(), wc))


def get_pw(cfg, args):
    accs = get_pwds(args.host, args.user, cfg['global']['datapath'],
            cfg['gnupg'].getboolean('use_agent'), cfg['gnupg']['gpg_path'],
            cfg['gnupg']['home'], args.gnupgpass)
    print_result(accs, args.host, args.user)


def list_accs(cfg, args):
    accounts = get_all_passwords(cfg['global']['datapath'])
    matches = accounts.search(args.host, args.user)
    accs = []
    # matches will be all lowercase, we need to go through all accounts to find
    # their proper capitalization
    for h, u in matches:
        (_h, _u, path) = accounts.get(h, u)
        accs.append((_h, _u, ''))
    print_result(accs, args.host, args.user)


def get_unique_password(host, user, datapath, use_agent, gpg_path, gnupghome, gnupgpass):
    pwds = get_pwds(host, user, datapath, use_agent, gpg_path, gnupghome, gnupgpass)
    if not pwds:
        raise KeyError
    elif len(pwds) > 1:
        raise RuntimeError
    else:
        return pwds[0][2].rstrip()


def pipe_pw(cfg, args):
    try:
        pwd = get_unique_password(args.host, args.user, cfg['global']['datapath'],
                cfg['gnupg'].getboolean('use_agent'), cfg['gnupg']['gpg_path'],
                cfg['gnupg']['home'], args.gnupgpass)
    except KeyError:
        print("No matches for host '{}' {}".format(args.host,
            "and user '{}'".format(args.user) if args.user is not None else ''),
            file=sys.stderr)
        sys.exit(1)
    except RuntimeError:
        print("Multiple matches for host '{}' {}".format(args.host,
            "and user '{}'".format(args.user) if args.user is not None else ''),
            file=sys.stderr)
        sys.exit(1)

    print(pwd)


def _rm_pw(datapath, host, user, pwfile):
    def do_rm(pwfile, host, user):
        git = Git(datapath)
        with GitTransaction(git):
            if git.has_origin():
                git.rebase_origin_master()
            git.rm(pwfile)
            git.commit("{}/{}: remove\n\n{}".format(
                host, user, get_version()))
            if git.has_origin():
                git.push_master()

    debug("Removing password for account '{}/{}'".format(host, user))

    attempt_retry(do_rm, pwfile, host, user)
    try:
        os.rmdir(os.path.dirname(pwfile))
    except OSError as e:
        if e.errno == errno.ENOTEMPTY:
            debug("More accounts exist for '{}', not removing host".format(host))
    else:
        debug("No more accounts exist for '{}', host removed".format(host))


def rm_pw(cfg, args):
    accounts = get_all_passwords(cfg['global']['datapath'])
    if not accounts.exists(args.host, args.user):
        sys.exit("User {} on args.host {} does not exist".format(args.user, args.host))
    (_, _, pwfile) = accounts.get(args.host, args.user)
    _rm_pw(cfg['global']['datapath'], args.host, args.user, pwfile)
    print("Password for user {} on host {} removed".format(args.user, args.host))


def replace_pw(cfg, args):
    return add_pw(cfg, args, exist_ok=True)


def _sync_pws(datapath, force, dec_gpg, enc_gpg):
    accounts = get_all_passwords(datapath)

    git = Git(datapath)
    with GitTransaction(git):
        num = 0
        if git.has_origin():
            git.rebase_origin_master()
        for (host, user, path) in accounts.iterate():
            if force or enc_gpg.get_file_recipients(path) != enc_gpg.get_recipient_fps():
                debug('Need to reencrypt {}'.format(path))
                encpw = enc_gpg.encrypt(dec_gpg.decrypt_file(path))
                write_and_add(git, path, encpw, True)
                num += 1

        if num > 0:
            uids = ''.join(['    - {}\n'.format(x) for x in enc_gpg.get_recipient_uids()])
            git.commit("Synchronized and reencrypted {} passwords to {} recipient{}{}:\n\n{}\n\n{}".format(
                num, enc_gpg.get_num_recipients(), 's' if enc_gpg.get_num_recipients() > 1 else '',
                ' (forced)' if force else '', uids, get_version())
            )
            if git.has_origin():
                git.push_master()
    return num


def sync_pws(cfg, args):
    if not 'ldap' in cfg:
        ldap = None
    else:
        ldap = cfg['ldap']

    keys = get_all_pubkeys(get_fps_from_conf(cfg), ldap,
            cfg['gnupg'].getboolean('use_agent'), cfg['gnupg']['home'])

    with GPG(gpg_path=cfg['gpg_path'], use_agent=False) as enc_gpg:
        for email, fps in keys.items():
            debug('Encrypting to {} ({} key{})'.format(
                email, len(fps), 's' if len(keys) > 1 else ''))
            for fp in fps:
                enc_gpg.add_recipient(fp)

        with GPG(use_agent=cfg['gnupg'].getboolean('use_agent'),
                gpg_path=cfg['gnupg']['gpg_path'],
                gnupghome=cfg['gnupg']['home']) as dec_gpg:
            if not cfg['gnupg'].getboolean('use_agent'):
                # gpg-agent should automatically popup a different password dialog so
                # we should only ask for the password if we're not using it
                dec_gpg.set_passphrase(args.gnupgpass)

            num = attempt_retry(_sync_pws, cfg['global']['datapath'], args.force,
                    dec_gpg, enc_gpg)

    if num == 0:
        print("No synchronization necessary, recipient lists were correct.")
    else:
        print("Successfully reencrypted {} passwords to {} recipients".format(
            num, enc_gpg.get_num_recipients()))


def update_repo(cfg, args):
    datapath = cfg['global']['datapath']
    git = Git(datapath)
    with GitTransaction(git):
        if git.has_origin():
            git.rebase_origin_master()
            print('Password database updated from origin')
        else:
            print('Cannot update: no git origin configured')


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
    'type': str,
    'metavar': 'HOSTFQDN',
    'default': None,
}

USER_ARG = {
    'action': 'store',
    'help': "Username for which the password is valid (e.g. 'root')",
    'nargs': None,
    'type': str,
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
                    'type': str,
                    'metavar': 'USER',
                    'help': 'Username (if omitted, list all passwords on HOSTFQDN)',
                }),
            ],
            'opt_args': {},
        },
        'list': {
            'help': 'List all accounts matching host and user',
            'method': list_accs,
            'pos_args': [
                ('host', HOST_ARG),
                ('user', {
                    'action': 'store',
                    'nargs': '?',
                    'type': str,
                    'metavar': 'USER',
                    'help': 'Username (if omitted, list all passwords on HOSTFQDN)',
                }),
            ],
            'opt_args': {},
        },
        'pipe': {
            'help': 'Get exactly one password and print on stdout (errors on stderr)',
            'method': pipe_pw,
            'pos_args': [
                ('host', HOST_ARG),
                ('user', {
                    'action': 'store',
                    'nargs': '?',
                    'type': str,
                    'metavar': 'USER',
                    'help': 'Username',
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
            'method': sync_pws,
            'pos_args': [],
            'opt_args': {
                '-f': {
                    'long': '--force',
                    'action': 'store_true',
                    'default': False,
                    'help': 'Always reencrypt all passwords (do not care about existing recipient list)',
                },
            },
        },
        'update': {
            'help': 'Update local password database from origin',
            'method': update_repo,
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
            help='Override path to key data store directory',
            action='store', type=str, metavar='PATH', default=None)

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
                    action=_val['action'], help=_val['help'])

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

    with GlobalLock(cfg['global']['datapath']):
        return actions[args.action]['method'](cfg, args)


if __name__ == '__main__':
    main()
