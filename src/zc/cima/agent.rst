=========================
Agent tests/documentation
=========================

Creation and configuration
==========================

The agent is run as a daemon, or under cron.  When it runs as a
daemon, it runs roughly every minute in a loop.

To create an agent, pass a configuration file specifying:

- A configuration directory.

- A database definition.

- An alerter definition.

Define a configuration file::

  [agent]
  directory = agent.d
  timeout = 1

  [database]
  class = zc.cima.tests:MemoryDB

  [alerter]
  class = zc.cima.tests:OutputAlerter

.. -> src

   >>> with open('agent.cfg', 'w') as f:
   ...     f.write(src)

Create the configuration directory::

  >>> import os
  >>> os.mkdir('agent.d')

Let's configure a basic check::

  [foo.txt]
  command = PY filecheck.py foo.txt

.. -> src

   >>> import sys
   >>> with open(os.path.join('agent.d', 'test.cfg'), 'w') as f:
   ...     f.write(src.replace('PY', sys.executable))

Some notes on check names and configurations.

Each check has a name, of the form: ``HOST/FILE/NAME``.

The configuration file name (without the ``.cfg`` suffix) must, of
course, be unique to a host.  Typically, the name should be based on a
unique deployment name for some application.

The configuration files follow the standard Python ConfigParser format.
Each section names a test.  Options:

command
  The command to run to perform the test.

interval
  How often should tests be performed, in multiple's of the agent's
  underlying interval (typically a minute). Defaults to 1.

retry
  How many times to retry after a failure.  Defaults to 3. To alert
  immediately on a failure, use 0.

retry_interval
  How quickly to retry. Defaults to 1.

(In the future, we might add additional options for accessing sockets
 rather than running commands, for setting metrics thresholds, etc.)

Now, let's create an agent:

    >>> import zc.cima.agent
    >>> agent = zc.cima.agent.Agent('agent.cfg')

We can see tit has the check:

    >>> [check.name for check in agent.checks]
    ['//test.example.com/test/foo.txt']

Normally, we'd run cima's main program, which creates an agent and
calls it's ``loop`` method, which calls ``perform`` in a loop, but for
now, we'll call ``perform`` method ourselves.

The perform method takes an argument that's a sort of a counter used
for scheduling.  The value is an interval number, normally since
the epoch.  It uses this to decide whether a particular check should
be performed, based on the check's interval, retry count and retry
policy.

In this test, we're using a configuration that always runs checks
every interval, so we'll always pass 0.

    >>> agent.perform(0)

The file we were checking for wasn't there, but we didn't get an
alert. Let's look at our database:

    >>> print agent.db
    {'agents': {'test.example.com': 1417804927.88},
     'faults': {'test.example.com': [{'message':
                                      "'foo.txt' doesn't exist\n (1 of 4)",
                                      'name': '//test.example.com/test/foo.txt',
                                      'severity': 40}]}}

The database includes informatiomn about the agents last activity. In
particular, it shows the time of the last activity, which is used by a
meta monitor to detect dead agents.

We didn't get alert because our default policy is to retry up to 3
times.

Retry
=====

Let's perform until we get an alert:

    >>> agent.perform(0)
    >>> agent.perform(0)
    >>> agent.perform(0)
    OutputAlerter trigger //test.example.com/test/foo.txt
    'foo.txt' doesn't exist
    <BLANKLINE>

If we keep performing, we don't get new alerts:

    >>> agent.perform(0)

If we create a file, we'll clear the alert:

    >>> open('foo.txt', 'w').close()
    >>> agent.perform(0)
    OutputAlerter resolve //test.example.com/test/foo.txt

If we look at the database, we'll see we still have a warning:

    >>> print agent.db
    {'agents': ...
     'faults': {'test.example.com': [{'message':
                                      "'foo.txt' exists, but is empty\n",
                                      'name': '//test.example.com/test/foo.txt',
                                      'severity': 30}]}}

Let's fix it:

    >>> with open('foo.txt', 'w') as f:
    ...     f.write('tester was here')
    >>> agent.perform(0)
    >>> print agent.db
    {'agents': ...
     'faults': {'test.example.com': []}}

Dealing with misbehaving checks
===============================

Some edge cases:

Nagios plugin wrote to stderr:

    >>> with open('foo.txt', 'w') as f:
    ...     f.write('stderr')
    >>> agent.perform(0)
    >>> print agent.db
    {'agents': ...
     'faults': {'test.example.com': [{'message': 'what hapenned? (1 of 4)',
                                      'name':
                              '//test.example.com/test/foo.txt#monitor-stderr',
                                      'severity': 40}]}}

Nagios plugin didn't write to stdout:

    >>> with open('foo.txt', 'w') as f:
    ...     f.write('noout')
    >>> agent.perform(0)
    >>> print agent.db
    {'agents': ...
     'faults': {'test.example.com': [{'message': ' (2 of 4)',
                      'name': '//test.example.com/test/foo.txt#monitor-no-out',
                                      'severity': 40}]}}

Nagios plugin returned a unknown status code:

    >>> with open('foo.txt', 'w') as f:
    ...     f.write('status')
    >>> agent.perform(0)
    >>> print agent.db
    {'agents': ...
     'faults': {'test.example.com': [{'message': "'foo.txt' exists\n (3 of 4)",
                      'name': '//test.example.com/test/foo.txt#monitor-status',
                                      'severity': 40}]}}

Squelch
=======

We can squelch alerts using regular expressions stored in the
database.  You must provide a reason for the squelch, as well as an
indication of who created it.  Squelches are set by external
applications. They record the time at which the squelch was set:

    >>> agent.db.squelch('test', 'testing', 'me')
    >>> pprint(agent.db.squelches)
    {'test': {'reason': 'testing', 'time': 1417968068.01, 'user': 'me'}}

    >>> agent.perform(0)
    >>> agent.perform(0)
    >>> print agent.db
    {'agents': ...
          'faults': {'test.example.com': [{'message': "'foo.txt' exists\n",
                      'name': '//test.example.com/test/foo.txt#monitor-status',
                                      'severity': 50}]}}

Here, we didn't get an alert, even though we has a critical fault.

We'll unsquelch:

    >>> agent.db.unsquelch('test')
    >>> agent.perform(0)
    OutputAlerter trigger //test.example.com/test/foo.txt#monitor-status
    'foo.txt' exists

JSON
====

We allow monitors to return their results as JSON.  Out funky file
checker will return file contents of they're JSON:

    >>> with open('foo.txt', 'w') as f:
    ...     f.write('{"faults": []}')
    >>> agent.perform(0)
    OutputAlerter resolve //test.example.com/test/foo.txt#monitor-status
    >>> print agent.db
    {'agents': ...
     'faults': {'test.example.com': []}}

We generate a fault of json is malformed or lacks a faults property:

    >>> with open('foo.txt', 'w') as f:
    ...     f.write('{"faults": []')
    >>> agent.perform(0)
    OutputAlerter trigger //test.example.com/test/foo.txt#json-error
    ValueError: Expecting object: line 1 column 14 (char 13)

    >>> with open('foo.txt', 'w') as f:
    ...     f.write('{')
    >>> agent.perform(0)
    OutputAlerter trigger //test.example.com/test/foo.txt#json-error
    ValueError: Expecting object: line 1 column 2 (char 1)
    >>> with open('foo.txt', 'w') as f:
    ...     f.write('{}')
    >>> agent.perform(0)
    OutputAlerter trigger //test.example.com/test/foo.txt#json-error
    KeyError: 'faults'
    >>> with open('foo.txt', 'w') as f:
    ...     f.write('{"faults": 1}')
    >>> agent.perform(0)
    OutputAlerter trigger //test.example.com/test/foo.txt#json-error
    TypeError: 'int' object is not iterable
    >>> with open('foo.txt', 'w') as f:
    ...     f.write('{"faults": [{}]}')
    >>> agent.perform(0)
    OutputAlerter trigger //test.example.com/test/foo.txt#json-error
    KeyError: 'severity'

Timeouts
========

If a test takes too long we'll get a timeout fault:

    >>> with open('foo.txt', 'w') as f:
    ...     f.write('sleep')
    >>> agent.perform(0)
    OutputAlerter trigger //test.example.com/test/foo.txt#monitor-timeout
    OutputAlerter resolve //test.example.com/test/foo.txt#json-error

Critical severity alerts immediately, no retry
==============================================

A monitor that returns JSON can return a CRITICAL serverity. If it
does, then we'll alert immediately.  We don't retry:

    >>> with open('foo.txt', 'w') as f:
    ...     f.write('{"faults": []}')
    >>> agent.perform(0)
    OutputAlerter resolve //test.example.com/test/foo.txt#monitor-timeout
    >>> with open('foo.txt', 'w') as f:
    ...     f.write('{"faults": [{"message": "Panic!", "severity": 50}]}')
    >>> agent.perform(0)
    OutputAlerter trigger //test.example.com/test/foo.txt Panic!

    >>> print agent.db
    {'agents': ...
     'faults': {'test.example.com': [{u'message': u'Panic!',
                                      'name': '//test.example.com/test/foo.txt',
                                      u'severity': 50}]}}

    >>> with open('foo.txt', 'w') as f:
    ...     f.write(
    ...      '{"faults": [{"message": "Panic!", "severity": 99, "name": "OMG"}]}')
    >>> agent.perform(0)
    OutputAlerter trigger //test.example.com/test/foo.txt#OMG Panic!
    OutputAlerter resolve //test.example.com/test/foo.txt

    >>> print agent.db
    {'agents': ...
          'faults': {'test.example.com': [{u'message': u'Panic!',
                                u'name': u'//test.example.com/test/foo.txt#OMG',
                                      u'severity': 99}]}}

Checks can use severity names
=============================

Monitors can use the strings, WARNING, INFO, and CRITICAL (any case)
for severities:

    >>> with open('foo.txt', 'w') as f:
    ...     f.write('{"faults": [{"message": "Worry", "severity": "WARNING"}]}')
    >>> agent.perform(0)
    OutputAlerter resolve //test.example.com/test/foo.txt#OMG
    >>> print agent.db
    {'agents': ...
     'faults': {'test.example.com': [{u'message': u'Worry',
                                      'name': '//test.example.com/test/foo.txt',
                                      u'severity': 30}]}}

    >>> with open('foo.txt', 'w') as f:
    ...     f.write('{"faults": [{"message": "Bad", "severity": "Error"}]}')
    >>> agent.perform(0)
    >>> print agent.db
    {'agents': ...
     'faults': {'test.example.com': [{u'message': u'Bad (1 of 4)',
                                      'name': '//test.example.com/test/foo.txt',
                                      u'severity': 40}]}}

    >>> with open('foo.txt', 'w') as f:
    ...   f.write('{"faults": [{"message": "Panic!", "severity": "critical"}]}')
    >>> agent.perform(0)
    OutputAlerter trigger //test.example.com/test/foo.txt Panic!
    >>> print agent.db
    {'agents': ...
     'faults': {'test.example.com': [{u'message': u'Panic!',
                                      'name': '//test.example.com/test/foo.txt',
                                      u'severity': 50}]}}

Loading state on startup
========================

On startup, the agent loads faults so it can resolve faults that have
cleared and avoid re-alerting on ones that haven't.  Out test database
implementation allows us to specify initial faults to test this::

  [agent]
  directory = agent.d
  timeout = 1

  [database]
  class = zc.cima.tests:MemoryDB
  faults = {"test.example.com": [{"message": "Badness",
                                  "name": "//test.example.com/test/foo.txt",
                                  "severity": 50}]}

  [alerter]
  class = zc.cima.tests:OutputAlerter

.. -> src

   >>> with open('agent.cfg', 'w') as f:
   ...     f.write(src)

If we perform a chech that succeeds, the previous fault will be resolved:

    >>> agent = zc.cima.agent.Agent('agent.cfg')
    >>> with open('foo.txt', 'w') as f:
    ...     f.write('test')
    >>> agent.perform(0)
    OutputAlerter resolve //test.example.com/test/foo.txt
