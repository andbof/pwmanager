[![Build Status](https://travis-ci.org/andbof/pwmanager.svg?branch=master)](https://travis-ci.org/andbof/pwmanager)

# pwmanager

pwmanager is a python script for storing passwords, searchable by hostname and
user, in a gnupg encrypted git backed database. It can encrypt to multiple keys
and also fetch keys from LDAP, allowing you to easily and securely share and
version control passwords with others. Useful for both personal and group-wide
password storage and sharing.

Copyright (C) 2019 Andreas Bofjäll <andreas@gazonk.org>, see LICENSE for
licensing details.

# Where to get it

The latest release is available at PyPI: https://pypi.org/project/pwmanager/

Source code repository is at github: https://github.com/andbof/pwmanager

# Basic installation

Quickest and easiest is to install using ``pip3`` from PyPI as your local user:

    pip3 install --user pwmanager

You can also install the latest development version directly from the github
repository:

    pip3 install --user git+git://github.com/andbof/pwmanager.git

Some options need to be set in the configuration file. A sample
``pwmanager.conf`` (``pwmanager.conf.sample``) is included in the package. pip3
will install it in the ``pwmanager/data`` subdirectory of the appropriate
python ``site-packages`` directory. It should be put in ``$HOME/.pwmanager/``

The standard location for your password repository is ``$HOME/.pwmanager/data``

pwmanager requires python3 >= 3.4 and some extra packages, see ``setup.py`` for
details. Python 2.x is not supported.

# Using it

## Getting help

    pwmanager -h

Help on actions is available by appending -h:

    pwmanager add -h

## Storing passwords

Adding the password ``secretpass`` for the account ``root`` on
``host.company.com`` to the database:

    pwmanager add host.company.com root secretpass

If you leave out ``secretpass``, pwmanager will prompt you for the
password.

## Retrieving passwords

Retrieving the password stored above:

    pwmanager get host.company.com root

Note ``pwmanager get`` matches both the hostname and username as substrings and
if you do not specify a username it will list all accounts, so all of these
will find the above account (and maybe others):

    pwmanager get host.company.com roo
    pwmanager get host.company.com oot
    pwmanager get host.company.com r
    pwmanager get host.company.com r
    pwmanager get host.company.co
    pwmanager get com
    pwmanager get h

## Synchronizing with others

pwmanager will always update from and push to ``origin`` when there is an
``origin`` git remote configured. git adds ``origin`` automatically if you
clone an already existing repository, but you need to add it manually if you
initialize it yourself or use ``pwmanager init``.

To add a remote repository later, use the normal git way:

    cd /path/to/datastore
    git remote add origin URL

In normal operation, pwmanager will, before doing anything, always fetch and
rebase on the latest ``origin/master``, and will push to ``origin/master``
afterwards. It will also retry this up to five times in case multiple people
are in a rebase-race and pushing at the same time. However, if you just added a
new origin remote it's a good idea to manually run:

    git fetch origin
    git rebase origin/master

If any of the two commands above fail, you need to fix whatever git complains
about or pwmanager will not work.


# How are the passwords stored?
(_aka When the script doesn't work and you desperately need a password_)

All passwords are stored in separate files, one per password, in your datadir.
They are encrypted using GnuPG to all keys you configured to use, so if you
have a suitable key available in your local gnupg keyring and you want the
password for 'user' on 'host', you can do so by just running gnupg:

    gpg -o - -d datadir/host/user.gpg

If this fails, ensure you have your secret key in your gnupg keyring.

Why is every password in a separate file, you ask? Because that enables
replacing individual passwords without having access to any secret key. This
allows automated password rotation, for example.

# Troubleshooting

## Decryption failed

gnupg could probably not find your secret key. Make sure your secret key is
available in your standard keyring in ``~/.gnupg`` and that you're running the
latest gnupg 2.x series.

For debian stretch you need to install ``python3-gnupg`` from
stretch-backports.

If your system defaults to gnupg 1.x and your gnupg 2.x binary is called gpg2,
set ``gpg_path = gpg2`` in the ``[gnupg]`` section of ``pwmanager.conf``.

## RuntimeError: No recipients to encrypt to!

You haven't added any key fingerprints in ``pwmanager.conf`` and haven't
configured any other data source. There are simply no public keys configured to
encrypt to.

## "I don't understand how to get the LDAP stuff working at all"

pwmanager currently assumes you have a group (``objectClass: posixGroup``) with
a ``memberUid`` attribute for every member. Those should map to whatever you've
set as ``user_attr`` in ``pwmanager.conf``.

Next, pwmanager assumes the user has the attribute you've set as ``key_attr``,
which should be the DN of a PGP keyserver compatible entry under ``key_dn``,
normally ``ou=PGP Keys,dc=company,dc=com``.

The same LDAP server must be able to act as a PGP compatible keyserver (hint:
``gpg --send-keys`` should work). Also, don't forget to uncomment the
``[ldap]`` header in ``pwmanager.conf``.

# Known issues

- pwmanager does not call ``mlock()``, mostly because doing so would require
  calling ``mlock()`` for the entire ~5 MB python binary.

- pwmanager currently does not support multiple git remotes. That should
  probably be implemented, for numerous reasons.
