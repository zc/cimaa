##############################################################################
#
# Copyright (c) Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
from zope.testing import renormalizing, setupstack
import doctest
import gevent
import json
import manuel.capture
import manuel.doctest
import manuel.testing
import mock
import os
import pdb
import pprint
import re
import time
import unittest

import zc.cima.pagerduty # See if grequest monkey-patching breaks other things

class Logging:

    trace = True

    def log(self, *args):
        if self.trace:
            print self.__class__.__name__, ' '.join(args)

class MemoryDB:

    def __init__(self, config):
        self.agents = {}
        self.faults = json.loads(config.get('faults', '{}'))
        self.squelches = {}

    def get_faults(self, agent):
        return self.faults.get(agent, ())

    def set_faults(self, agent, faults):
        self.faults[agent] = faults
        self.agents[agent] = time.time()

    def get_squelches(self):
        return list(self.squelches)

    def squelch(self, regex, reason, user):
        self.squelches[regex] = dict(
            reason = reason,
            user = user,
            time = 1417968068.01
            )

    def unsquelch(self, regex):
        del self.squelches[regex]

    def __str__(self):
        return pprint.pformat(dict(
            agents=self.agents, faults=self.faults))

class OutputAlerter(Logging):

    nfail = 0
    sleep = 0.0

    def __init__(self, config):
        pass

    def fail(self):
        if self.nfail > 0:
            self.nfail -= 1
            raise ValueError('fail')
        gevent.sleep(self.sleep)

    def trigger(self, name, message):
        self.fail()
        self.log('trigger', name, message)

    def resolve(self, name):
        self.fail()
        self.log('resolve', name)


def setUp(test):
    setupstack.setUpDirectory(test)
    test.globs.update(
        pdb = pdb,
        pprint = pprint.pprint,
        )
    with open(os.path.join(os.path.dirname(__file__), 'filecheck_py')) as src:
        with open('filecheck.py', 'w') as dest:
            dest.write(src.read())

    setupstack.context_manager(
        test, mock.patch('socket.getfqdn', return_value='test.example.com'))

def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    suite = unittest.TestSuite((
        manuel.testing.TestSuite(
            manuel.doctest.Manuel(
                optionflags=optionflags,
                checker=renormalizing.OutputChecker([
                    (re.compile(r"'agents': {'test.example.com': \d+(\.\d*)?"),
                     "'agents': {'test.example.com': ")
                    ])
                ) + manuel.capture.Manuel(),
            'agent.rst',
            'schedule.rst',
            setUp=setUp, tearDown=setupstack.tearDown),
        ))
    if 'DYNAMO_TEST' in os.environ:
        suite.addTest(
            manuel.testing.TestSuite(
                manuel.doctest.Manuel(
                    optionflags=optionflags,
                    checker=renormalizing.OutputChecker([
                        (re.compile(r"Decimal\('\d+(\.\d*)?'\)"), "")
                        ])
                    ) + manuel.capture.Manuel(),
                'dynamodb.rst',
                setUp=setUp, tearDown=setupstack.tearDown),
            )
    return suite
