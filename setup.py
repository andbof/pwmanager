#!/usr/bin/python3

import os
from setuptools import setup, find_packages

project_name = 'pwmanager'

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
        name = project_name,
        version = "1.1",
        author = 'Andreas Bofjäll',
        author_email = 'andreas@gazonk.org',
        description = 'Manage passwords in a git backed encrypted gnupg database with LDAP support',
        long_description = read(os.path.join(os.path.dirname(__file__), 'README.md')),
        install_requires = [
            'ldap3',
            'python-gnupg >= 0.4.0',     # 0.3.9 throws "Decryption failed"
        ],
        license = "MIT",
        keywords = "password manager gpg gnupg ldap",
        url = "https://github.com/andbof/pwmanager",
        package_dir = {'': 'src'},
        packages = find_packages('src'),
        package_data = {
            'pwmanager': ['data/*'],
        },
        entry_points = {
            'console_scripts': ['pwmanager = pwmanager.pwmanager:main'],
        },
        test_suite = 'tests',
        classifiers = [
            "Development Status :: 4 - Beta",
            "Environment :: Console",
            "Topic :: Utilities",
            "License :: OSI Approved :: MIT License",
        ],
)
