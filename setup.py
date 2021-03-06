##############################################################################
#
# Copyright (c) Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
name, version = 'zc.cimaa', '0'

install_requires = ['setuptools', 'gevent']
extras_require = dict(
    test      = ['manuel', 'mock', 'zope.testing'],
    dynamodb  = ['boto', 'keyring'],
    pagerduty = ['grequests'],
    sentry    = ['raven'],
    slack     = ['slacker'],
    zconfig   = ['ZConfig'],
    )
extras_require['all'] = reduce((lambda a, b: a + b),
                               (i[1] for i in extras_require.items()
                                if i[0] != 'test'))
extras_require['test'] += extras_require['all']

entry_points = """
[console_scripts]
agent = zc.cimaa.agent:main
meta-check = zc.cimaa.meta:main
setup-dynamodb = zc.cimaa.dynamodb:setup
squelch = zc.cimaa.squelch:squelch
unsquelch = zc.cimaa.squelch:unsquelch
"""

from setuptools import setup

long_description=open('README.rst').read()

setup(
    author = 'Jim Fulton',
    author_email = 'jim@zope.com',
    license = 'ZPL 2.1',
    url = 'https://github.com/zc/cimaa',
    name = name, version = version,
    long_description = long_description,
    description = long_description.strip().split('\n')[1],
    packages = [name.split('.')[0], name],
    namespace_packages = [name.split('.')[0]],
    package_dir = {'': 'src'},
    install_requires = install_requires,
    zip_safe = False,
    entry_points=entry_points,
    package_data = {name: ['*.txt', '*.rst']},
    extras_require = extras_require,
    tests_require = extras_require['test'],
    test_suite = name+'.tests.test_suite',
    )
