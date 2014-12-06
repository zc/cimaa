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
import json
import manuel.capture
import manuel.doctest
import manuel.testing
import mock
import os
import pprint
import re
import time
import unittest

class Logging:

    trace = True

    def log(self, *args):
        if self.trace:
            print self.__class__.__name__, ' '.join(args)

class MemoryDB:

    def __init__(self, config):
        self.agents = {}
        self.alerts = {}
        self.faults = json.loads(config.get('faults', '{}'))
        self.squelches = []

    def heartbeat(self, agent, status):
        self.agents[agent] = dict(
            agent=agent,
            updated=time.time(),
            status=status)

    def old_agents(self, min_age):
        now = time.time()
        for data in agents.values():
            agent_age = now - data['updated']
            if agent_age > min_age:
                yield data.copy()

    def alert_start(self, name):
        self.alerts[name] = time.time()

    def alert_finished(self, name):
        self.alerts.pop(name, None)

    def old_alerts(self, min_age):
        now = time.time()
        for name, start in alerts.items():
            age = now - start
            if age > min_age:
                yield name

    def get_faults(self, agent):
        return self.faults.get(agent)

    def set_faults(self, agent, faults):
        self.faults[agent] = faults

    def get_squelches(self):
        return list(self.squelches)

    def __str__(self):
        return pprint.pformat(dict(
            agents=self.agents, alerts=self.alerts, faults=self.faults))

class OutputAlerter(Logging):

    def __init__(self, config):
        pass

    def trigger(self, name, message):
        self.log('trigger', name, message)

    def resolve(self, name):
        self.log('resolve', name)


def setUp(test):
    setupstack.setUpDirectory(test)
    with open(os.path.join(os.path.dirname(__file__), 'filecheck_py')) as src:
        with open('filecheck.py', 'w') as dest:
            dest.write(src.read())

    setupstack.context_manager(
        test, mock.patch('socket.getfqdn', return_value='test.example.com'))

def test_suite():
    return unittest.TestSuite((
        manuel.testing.TestSuite(
            manuel.doctest.Manuel(
                optionflags=doctest.NORMALIZE_WHITESPACE|doctest.ELLIPSIS,
                checker=renormalizing.OutputChecker([
                    (re.compile(r"'updated': \d+(\.\d*)?"), '')
                    ])
                ) + manuel.capture.Manuel(),
            'agent.rst', 'schedule.rst',
            setUp = setUp, tearDown=setupstack.tearDown),
        ))

