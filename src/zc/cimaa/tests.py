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
import zc.cimaa.stub

def MetaDB(conf):
    "Database that retains state accross factory calls"
    return meta_db

def setUpSlack(test):
    import slacker
    token = os.environ['SLACK_TOKEN']
    channel = os.environ.get('SLACK_CHANNEL') or 'general'
    slack = slacker.Slacker(token)
    channel_list = slack.channels.list()
    channel_list = channel_list.body['channels']
    chan_map = {x['name']: x for x in channel_list}
    assert channel in chan_map
    if chan_map[channel]['is_archived']:
        import warnings
        warnings.warn("Unarchiving test channel. Re-archive as desired")
        slack.channels.unarchive(chan_map[channel]['id'])
    test.globs.update(
        channel = channel,
        channel_id = chan_map[channel]['id'],
        token = token,
        pprint = pprint.pprint,
    )

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
    meta_db = zc.cimaa.stub.MemoryDB({})
    setupstack.context_manager(
        test, mock.patch('getpass.getuser', lambda: 'tester'))

def setUpTime(test):
    setUp(test)
    globs = test.globs
    globs['now'] = 1418487287.82
    setupstack.context_manager(
        test, mock.patch('time.time', side_effect=lambda: globs['now']))


def test_suite():
    optionflags = doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    time_pat = r"\d{5,}(\.\d+)?"
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
        doctest.DocTestSuite('zc.cimaa.threshold',
                             optionflags=optionflags,
                             setUp=setUpPP),
        doctest.DocTestSuite('zc.cimaa.agent', optionflags=optionflags),
        ))
    if 'DYNAMO_TEST' in os.environ:
        suite.addTest(
            manuel.testing.TestSuite(
                manuel.doctest.Manuel(
                    optionflags=optionflags,
                    checker=renormalizing.OutputChecker([
                        (re.compile(time_pat), "T")
                        ])
                    ) + manuel.capture.Manuel(),
                'dynamodb.rst',
                setUp=setUp, tearDown=setupstack.tearDown),
            )
    if 'SLACK_TOKEN' in os.environ:
        suite.addTest(
            doctest.DocFileSuite(
                'slack.rst', optionflags=optionflags,
                setUp=setUpSlack),
        )
    return suite
