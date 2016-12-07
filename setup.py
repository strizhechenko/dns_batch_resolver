#!/usr/bin/env python

'''The setup and build script for the twitterbot-farm library.'''

import os

from setuptools import setup, find_packages


def read(*paths):
    """Build a file path from *paths* and return the contents."""
    with open(os.path.join(*paths), 'r') as f:
        return f.read()


setup(
    name='dns_batch_resolver',
    version='0.0.2',
    author='Oleg Strizhechenko',
    author_email='oleg.strizhechenko@gmail.com',
    license='GPL',
    url='https://github.com/strizhechenko/dns_batch_resolver',
    keywords='dns batch resolver multithreaded ipv6 multiple servers',
    description='"Framework" for running a lot of twitterbots without useless twitter API calls.',
    long_description=(read('README.rst')),
    packages=find_packages(exclude=['tests*']),
    scripts=['utils/dns_batch_resolver', 'utils/__dns_batch_resolver.py'],
    install_requires=['dnspython', 'pyyaml'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: MacOS',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development',
        'Topic :: Utilities',
    ],
)
