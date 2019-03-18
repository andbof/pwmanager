#!/usr/bin/python3

import base64
from pwmanager.debug import debug
import ldap3
import os
import ssl
import sys

def get_dn_attribute(conn, dn, filtr, attr):
    """
    Return an attribute for the LDAP entry specified by dn.
    """
    debug("Getting LDAP attribute '{}' for DN={} with filter '{}'".format(attr, dn, filtr))
    r = conn.search(dn, filtr, attributes=[attr])
    if r == False or len(conn.entries) != 1:
        raise RuntimeError("dn '{}' filter '{}' return did not return exactly one hit".format(
            dn, filtr))

    if attr not in conn.entries[0]:
        return []
    return [x for x in conn.entries[0][attr]]


def get_one_dn_attribute(conn, dn, filtr, attr):
    """
    Return an attribute for the LDAP entry specified by dn and ensure it only
    occurs once.
    """
    l = get_dn_attribute(conn, dn, filtr, attr)
    if not len(l) == 1:
        sys.exit('{} does not have exactly one {} attribute!'.format(dn, attr))
    return l[0]


def get_group_members(conn, group_dn):
    return get_dn_attribute(conn, group_dn,
            '(objectClass=posixGroup)', 'memberUid')


def get_user_keydns(conn, ldap, uids):
    """
    Grab owner name + email and corresponding key attribute (e.g. fdUserKeyDN)
    records from LDAP. The key attribute should match into key_dn (e.g. "ou=PGP
    Keys,dc=company,dc=com").
    """
    r = {}
    for uid in uids:
        key_dns = get_dn_attribute(conn,
            '{}={},{}'.format(
                ldap['user_attr'], uid, ldap['base_dn']),
            '(objectClass=person)', ldap['key_attr'])
        if not key_dns:
            # Not all members may have a GPG key registered
            continue
        email = get_one_dn_attribute(conn,
            '{}={},{}'.format(
                ldap['user_attr'], uid, ldap['base_dn']),
            '(objectClass=person)', ldap['mail_attr'])
        name = get_one_dn_attribute(conn,
            '{}={},{}'.format(
                ldap['user_attr'], uid, ldap['base_dn']),
            '(objectClass=person)', ldap['name_attr'])
        owner = '{} <{}>'.format(name, email)
        if not owner in r:
            r[owner] = []
        r[owner].extend(key_dns)
    return r


def get_gpg_keys(conn, dns):
    """
    Grab pgpKeyInfo records (base64 encoded gpg keys) for the key attribute
    entries in LDAP, returning a dict {key_attr: pgpKeyInfo}
    """
    r = {}
    for dn in dns:
        data = get_dn_attribute(conn, dn, '(objectClass=pgpKeyInfo)',
            'pgpKey')
        if not data:
            # User had set a key that has been removed from the keyserver
            continue
        if len(data) != 1:
            raise RuntimeError("key_attr '{}' matches multiple keys!".format(dn))

        # ldap3 seems to base64 decode the key data for us,
        # but we don't want that.
        r[dn] = base64.b64encode(data[0].encode("utf-8"))
    return r


def flatten(lists):
    return [x for sublist in lists for x in sublist]


def get_ldap_group_keys(ldap, pw):
    """
    Return a dict
        {"firstname lastname <email@domain>": "base64 encoded pgp key"}
    for all members of the configured LDAP group.
    """
    if not os.path.exists(ldap['ca_cert']):
        raise RuntimeError('{} does not exist, check LDAP config'.format(ldap['ca_cert']))

    tls_conf = ldap3.Tls(validate=ssl.CERT_REQUIRED, version=ssl.PROTOCOL_TLSv1_2,
            ca_certs_file=ldap['ca_cert'])
    srv = ldap3.Server(ldap['server'], port=ldap.getint('port'),
            use_ssl=ldap.getboolean('use_ssl'), tls=tls_conf)

    with ldap3.Connection(srv, ldap['bind_dn'], pw) as l:
        if not l.bind():
            raise RuntimeError('Could not bind to LDAP, wrong password?')

        members = sorted(get_group_members(l, ldap['group_dn']))
        key_dns = get_user_keydns(l, ldap, members)
        keys = get_gpg_keys(l, flatten(key_dns.values()))

    user_keys = {}
    for user, dns in key_dns.items():
        user_keys[user] = []
        for dn in dns:
            user_keys[user].append(keys[dn])

    return user_keys
