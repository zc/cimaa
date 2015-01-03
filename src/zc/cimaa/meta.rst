============
Meta Monitor
============

The cimaa meta monitor is used to monitor for stoped agents and for
long-lived global squelches.

Duplicate faults
----------------

The monitor will typically run in multiple agents, to avoid a single
point of monitoring failure. This means that we may issue multiple
alerts for a single problem.  Amongst the consequences of this:

- When configuring the meta monitor, use an "absolute" check name, like:
  ``//meta``.  This way, the fault names will be agent-independent.

- ``trigger`` might be called multiple times, by separate agents, for
  the same fault name. An alerter needs to handle this properly and
  not message humans multiple times because of trigger being called
  multiple times.  (Pager Duty does trigger de-duping, so it's alerter
  doesn't have to deal with this.)

Tests
=====

There's a meta-monitor entry point:

    >>> import pkg_resources
    >>> monitor = pkg_resources.load_entry_point(
    ...     'zc.cimaa', 'console_scripts', 'meta-monitor')

The monitor is run with the an agent configuration file as it's
argument. It uses the database definition::

  [database]
  class = zc.cimaa.tests:MetaDB

.. -> src

    >>> with open('agent.cfg', 'w') as f:
    ...     f.write(src)

If we run the monitor with an empty database:

    >>> monitor(['agent.cfg'])
    {"faults": []}

Inactive agents
---------------

Now, we'll update the database with some monitor data:

    >>> import time, zc.cimaa.tests
    >>> zc.cimaa.tests.meta_db.set_faults('a1', [], time.time() - 99)
    >>> zc.cimaa.tests.meta_db.set_faults('a2', [], time.time() - 199)
    >>> zc.cimaa.tests.meta_db.set_faults('a3', [], time.time() - 999)

    >>> monitor(['agent.cfg'])
    {"faults": [{"message": "Inactive agent", "name": "a2", "severity": 30},
                {"message": "Inactive agent", "name": "a3", "severity": 40}]}

Let's change our configuration to use a different agent base interval::

  [agent]
  base_interval = 30

  [database]
  class = zc.cimaa.tests:MetaDB

.. -> src

    >>> with open('agent.cfg', 'w') as f:
    ...     f.write(src)

::

    >>> monitor(['agent.cfg'])
    {"faults": [{"message": "Inactive agent", "name": "a1", "severity": 30},
                {"message": "Inactive agent", "name": "a2", "severity": 40},
                {"message": "Inactive agent", "name": "a3", "severity": 40}]}

And supply different warning and error levels:

    >>> monitor('-w4 -e10 agent.cfg'.split())
    {"faults": [{"message": "Inactive agent", "name": "a2", "severity": 30},
                {"message": "Inactive agent", "name": "a3", "severity": 40}]}

Global squelch in place too long
--------------------------------

The meta monitor also checks for squelches left in place too long:

    >>> zc.cimaa.tests.meta_db.squelch(
    ...     '.', 'testing', 'tester', time.time() - 3700)
    >>> monitor('-w4 -e10 agent.cfg'.split())
    {"faults": [{"message": "Inactive agent", "name": "a2", "severity": 30},
                {"message": "Inactive agent", "name": "a3", "severity": 40},
                {"message":
                 "Alerts squelched 61 minutes ago by tester because testing",
                 "name": "global-squelch", "severity": 40}]}

We can control how long the global squelch can be in place before
alerting by specifying an age in minutes:

    >>> monitor('-w99 -e99 -s99 agent.cfg'.split())
    {"faults": []}
