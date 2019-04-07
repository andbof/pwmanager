#!/usr/bin/python3

import configparser
import getpass
import os

DEFAULT_CONF_DIR = os.path.join(os.getenv('HOME'), '.pwmanager')
DEFAULT_CONF = os.path.join(DEFAULT_CONF_DIR, 'pwmanager.conf')
DEFAULT_GNUPG_HOME = os.path.join(os.getenv('HOME'), '.gnupg')

def parse(path):
    replace = {
            '{CONFDIR}': os.path.dirname(path),
            '{HOME}': os.getenv('HOME'),
            '{WHOAMI}': getpass.getuser(),
    }
    c = configparser.ConfigParser()
    c.read(path)

    # Replace {} replacement values in configuration file
    for s in c.sections():
        for k in c[s]:
            for r, v in replace.items():
                if r in c[s][k]:
                    c[s][k] = c[s][k].replace(r, v)

    # Some keys have default values if not specified
    if not 'keys' in c['global']:
        c['global']['keys'] = ''
    if not 'gpg_path' in c['gnupg']:
        # 'gpg' without absolute path is the same default as python3-gnupg uses
        c['gnupg']['gpg_path'] = 'gpg'

    return c


def print_sample(path):
    print(
        """
        # Configuration file for pwmanager
        # Comments start with '#'
        # These tokens can be used in any value:
        #   {CONFDIR}	Directory where this file is stored
        #   {HOME}	Home directory for current user
        #   {WHOAMI}	Username for currently logged in user

        [global]
        debug = no
        datapath = {CONFDIR}/data
        # Fingerprints of keys to encrypt to, separate multiple keys with comma.
        # This can be left out if another data source (e.g. LDAP) is used.
        #keys = fingerprint1,fingerprint2

        [gnupg]
        #gpg_path = gpg
        home = {HOME}/.gnupg
        use_agent = yes

        # LDAP configuration. Uncomment and configure to enable fetching keys from
        # LDAP. pwmanager will look at the {key} attribute for every user in {group},
        # matching {match} with the DN of keys found under the {key_dn} tree.
        #
        # The LDAP keyserver should be set up as a standard PGP keyserver.
        #[ldap]
        #group = company-admins
        # The FusionDirectory gpg plugin uses fdUserkeyDN to match users with keys
        #key_attr = fdUserKeyDN
        #server = ldap.company.com
        # Unencrypted and StartSSL LDAP are normally on 389 and always TLS on 636
        #port = 389
        #use_ssl = no
        #When using SSL, pwmanager will validate the certificate using the CA provided
        #ca_cert = /etc/ssl/certs/company_ca.pem
        #bind_dn = uid={WHOAMI},ou=people,dc=company,dc=com
        # pwmanager will prompt for LDAP password if bind_pw is left commented out
        #bind_pw = myldapsecret
        # base DN for user lookup
        #base_dn = ou=people,dc=company,dc=com
        # unique user attribute used for mapping with groups
        #user_attr = uid
        #key_dn = ou=PGP Keys,dc=company,dc=com
        #mail_attr = mail
        #name_attr = cn
        """
    )
