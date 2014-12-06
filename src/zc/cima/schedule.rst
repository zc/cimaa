Agent scheduling
================

The agent scedules based on a base time interval, typically a minute.
It endeavors to start tunning tests on time_interval boundaries.  All
other scheduling is done in terms of the base interval.  Further, when
tests have intervals larger than one, then the agent schedules them so
that they fall on even intervals, relative to the epoch. For example,
a test with an interval of 5, will run approximately evert 5 minutes
on the hour.

There are a number of pices that make up this:

- Check-specific scheduling rules

- A loop method that triggers an agent to perform checks on regular
  intervals, and

- Agent logic that decides which checks to run in any interval.

We'll look at each of these in turn.

Check rules
===========

The agend calls ``should_run`` on a check, passing in the current
interval number.  We'll look at this with a particular check:

    >>> import zc.cima.agent
    >>> check = zc.cima.agent.Check('//test', 'pwd', 5, 3, 2)

The check above runs on 5-minute interval, but, if there are failures,
it retries every 2 minutes.  Let's look at this as a scenario.

    >>> def runs(i, expect):
    ...     if check.should_run(i) != expect:
    ...         print 'wrong'
    >>> runs(0, True)
    >>> runs(1, False)
    >>> runs(2, False)
    >>> runs(3, False)
    >>> runs(4, False)
    >>> runs(5, True)
    >>> check.failures = 1
    >>> runs(6, False)
    >>> runs(7, True)
    >>> check.failures = 2
    >>> runs(8, False)
    >>> runs(9, True)
    >>> check.failures = 3
    >>> runs(10, False)
    >>> runs(11, True)
    >>> check.failures = 0
    >>> runs(12, False)
    >>> runs(13, False)
    >>> runs(14, False)
    >>> runs(15, True)
    >>> check.failures = 1
    >>> runs(16, False)
    >>> runs(17, True)
    >>> check.failures = 0
    >>> runs(18, False)
    >>> runs(19, False)
    >>> runs(20, True)

Let's look at some other schedules.

If the retry interval is 1, then we always should run if there are failures.

    >>> check = zc.cima.agent.Check('//test', 'pwd', 5, 3, 1)
    >>> runs(0, True)
    >>> runs(1, False)
    >>> runs(2, False)
    >>> runs(3, False)
    >>> runs(4, False)
    >>> runs(5, True)
    >>> check.failures = 1
    >>> runs(6, True)
    >>> runs(7, True)
    >>> runs(8, True)
    >>> runs(9, True)
    >>> runs(10, True)

    >>> check = zc.cima.agent.Check('//test', 'pwd', 5, 3, 3)
    >>> runs(0, True)
    >>> runs(1, False)
    >>> runs(2, False)
    >>> runs(3, False)
    >>> runs(4, False)
    >>> runs(5, True)
    >>> check.failures = 1
    >>> runs(6, False)
    >>> runs(7, False)
    >>> runs(8, True)
    >>> check.failures = 2
    >>> runs(9, False)
    >>> runs(10, False)
    >>> runs(11, True)
    >>> check.failures = 3
    >>> runs(12, False)
    >>> runs(13, False)
    >>> runs(15, True)
    >>> check.failures = 0
    >>> runs(16, False)
    >>> runs(17, False)
    >>> runs(18, False)
    >>> runs(19, False)
    >>> runs(20, True)

    >>> check = zc.cima.agent.Check('//test', 'pwd', 5, 3, 5)
    >>> runs(0, True)
    >>> runs(1, False)
    >>> runs(2, False)
    >>> runs(3, False)
    >>> runs(4, False)
    >>> runs(5, True)
    >>> check.failures = 1
    >>> runs(6, False)
    >>> runs(7, False)
    >>> runs(8, False)
    >>> runs(9, False)
    >>> runs(10, True)
    >>> check.failures = 2
    >>> runs(11, False)
    >>> runs(12, False)
    >>> runs(13, False)
    >>> runs(14, False)
    >>> runs(15, True)
    >>> check.failures = 3
    >>> runs(16, False)
    >>> runs(17, False)
    >>> runs(18, False)
    >>> runs(19, False)
    >>> runs(20, True)
    >>> check.failures = 0
    >>> runs(21, False)
    >>> runs(22, False)
    >>> runs(23, False)
    >>> runs(24, False)
    >>> runs(25, True)

loop
====

Agents have a loop method that compute integer interval number and
calls perform.  To support testing, you can optionally supply a
numnber of times to run.

Let's set up an agent::

  [agent]
  directory = agent.d
  base_interval = .1

  [database]
  class = zc.cima.tests:MemoryDB

  [alerter]
  class = zc.cima.tests:OutputAlerter

.. -> src

   >>> with open('agent.cfg', 'w') as f:
   ...     f.write(src)

Note that we set a base interval of .1 seconds (for testing). The default is 60.
You can use this option for speeding up checks if you need to.

Let's configure a basic check::

  [foo.txt]
  command = PY filecheck.py foo.txt
  interval = 5
  retry = 5

.. -> src

   >>> import os, sys
   >>> os.mkdir('agent.d')
   >>> with open(os.path.join('agent.d', 'test.cfg'), 'w') as f:
   ...     f.write(src.replace('PY', sys.executable))

Create an agent:

    >>> import zc.cima.agent
    >>> agent = zc.cima.agent.Agent('agent.cfg')

Let's see loop calls perform correctly:

    >>> ticks = []
    >>> agent.perform = ticks.append
    >>> import time
    >>> now = time.time()
    >>> agent.loop(9)
    >>> now = int(now/.1) + 1
    >>> ticks[0] in (now, now + 1)
    True
    >>> for i in range(1, len(ticks)):
    ...     if ticks[i] - ticks[i-1] != 1:
    ...         print 'bad'

Putting it together
===================

    >>> agent = zc.cima.agent.Agent('agent.cfg')

It's going to take at most 5 tries to get an error (because the file
being tested doesn't exists), but it will take a least 6 tries to get
a alert. Let's start by looping 5 times:

    >>> agent.loop(5)

At this point, we should have detected a fault:

    >>> faults = agent.db.get_faults(agent.name)
    >>> len(faults), faults[0]['name']
    (1, '//test.example.com/test/foo.txt')

5 more tries should be enough to go critical:

    >>> agent.loop(5)
    OutputAlerter trigger //test.example.com/test/foo.txt
    'foo.txt' doesn't exist

There's an entry point for running the agent:

    >>> import pkg_resources
    >>> main = pkg_resources.load_entry_point(
    ...     'zc.cima', 'console_scripts', 'agent')
    >>> main(['agent.cfg', '-n10'])
    OutputAlerter trigger //test.example.com/test/foo.txt
    'foo.txt' doesn't exist
