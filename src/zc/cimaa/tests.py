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
import logging
import manuel.capture
import manuel.doctest
import manuel.testing
import mock
import os
import pdb
import pprint
import re
import StringIO
import time
import unittest

import zc.cimaa.pagerduty # See if grequest monkey-patching breaks other things

class Logging:

    trace = True

    def log(self, *args):
        if self.trace:
            print self.__class__.__name__, ' '.join(args)

class MemoryDB:

    def __init__(self, config):
        self.faults = json.loads(config.get('faults', '{}'))
        self.squelches = {}
        self.agents = {}

    def old_agents(self, age):
        max_updated = time.time() - age
        return [dict(name=k, updated=v) for k, v in self.agents.items()
                if v < max_updated]


    def get_faults(self, agent):
        return self.faults.get(agent, ())

    def set_faults(self, agent, faults, now=None):
        times = dict((f[name], f['since'])
                     for f in self.faults.get('agent', ())
                     if f['name'])
        for f in faults:
            f['since'] = times.get(f['name'], f['updated'])
        self.faults[agent] = faults
        self.agents[agent] = now or time.time()

    def get_squelch(self, regex):
        return self.squelches.get(regex)

    def get_squelches(self):
        return sorted(self.squelches)

    def get_squelch_details(self):
        return [_squelch_detail(item)
                for item in sorted(self.squelches.items())]

    def squelch(self, regex, reason, user, permanent=False, now=None):
        self.squelches[regex] = dict(
            reason = reason,
            user = user,
            time = now or 1417968068.01,
            permanent = permanent,
            )

    def unsquelch(self, regex):
        del self.squelches[regex]

    def __str__(self):
        return pprint.pformat(self.faults)

def _squelch_detail(regex, data):
    data = data.copy()
    data['regex'] = regex
    return data

def MetaDB(conf):
    return meta_db

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

def OutputMetrics(config):
    def output_metrics(timestamp, name, value, units=''):
        print timestamp, name, value, units
    return output_metrics

def setUpPP(test):
    from json import dumps as original_dumps
    setupstack.context_manager(
        test,
        mock.patch('json.dumps',
                   lambda o: original_dumps(o, sort_keys=True))
        )
    test.globs.update(
        pdb = pdb,
        pprint = pprint.pprint,
        pp = pprint.pprint,
        )

def setUp(test):
    setUpPP(test)
    setupstack.setUpDirectory(test)
    with open(os.path.join(os.path.dirname(__file__), 'filecheck_py')) as src:
        with open('filecheck.py', 'w') as dest:
            dest.write(src.read())

    setupstack.context_manager(
        test, mock.patch('socket.getfqdn', return_value='test.example.com'))

    setupstack.context_manager(test, mock.patch('logging.basicConfig'))
    setupstack.context_manager(test, mock.patch('logging.getLogger'))
    setupstack.context_manager(
        test, mock.patch('raven.handlers.logging.SentryHandler'))
    setupstack.context_manager(test, mock.patch('ZConfig.configureLoggers'))
    global meta_db
    meta_db = MemoryDB({})

def setUpTime(test):
    setUp(test)
    globs = test.globs
    globs['now'] = 1418487287.82
    setupstack.context_manager(
        test, mock.patch('time.time', side_effect=lambda: globs['now']))


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    time_pat = r"\d+(\.\d*)?"
    suite = unittest.TestSuite((
        manuel.testing.TestSuite(
            manuel.doctest.Manuel(
                optionflags=optionflags,
                checker=renormalizing.OutputChecker([
                    (re.compile(r"'agents': {'test.example.com': "+time_pat),
                     "'agents': {'test.example.com': "),
                    (re.compile(r"'since': "+time_pat), 'SINCE'),
                    (re.compile(r"'updated': "+time_pat), 'UPDATED'),
                    ])
                ) + manuel.capture.Manuel(),
            'agent.rst', 'meta.rst', 'schedule.rst', 'squelch.rst',
            setUp=setUp, tearDown=setupstack.tearDown),
        manuel.testing.TestSuite(
            manuel.doctest.Manuel(
                optionflags=optionflags,
                ) + manuel.capture.Manuel(),
            'metrics.rst',
            setUp=setUpTime, tearDown=setupstack.tearDown),
        doctest.DocTestSuite('zc.cimaa.nagiosperf', optionflags=optionflags),
        doctest.DocTestSuite(
            'zc.cimaa.threshold', optionflags=optionflags,
            setUp=setUpPP),
        ))
    if 'DYNAMO_TEST' in os.environ:
        suite.addTest(
            manuel.testing.TestSuite(
                manuel.doctest.Manuel(
                    optionflags=optionflags,
                    checker=renormalizing.OutputChecker([
                        (re.compile(r"Decimal\('%s'\)" % time_pat), "T")
                        ])
                    ) + manuel.capture.Manuel(),
                'dynamodb.rst',
                setUp=setUp, tearDown=setupstack.tearDown),
            )
    return suite
