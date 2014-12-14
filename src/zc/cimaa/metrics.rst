===============
Metrics support
===============

Metrics are used in 2 ways in cimaa:

1. Generate/clear faults when certain metrics exceed thresholds and
   return to normal.

2. Metrics can be stored for analysis by sending them to a metrics
   stream, like log files or Kinesis.

When calling a Nagios plugin, performance data, if present is
converted to metric data. When calling a cimaa plugin (command that
returns JSON), the JSON data can include a metrics property which is a
sequence dictionaries with ``name``, ``value``, ``units`` and optional
``timestamp`` keys.

Saving metrics to a stream
==========================

When defining an agent, you can specify a ``metrics`` section to
specify a mtrics handler::

  [agent]
  directory = agent.d

  [database]
  class = zc.cimaa.tests:MemoryDB

  [alerter]
  class = zc.cimaa.tests:OutputAlerter

  [metrics]
  class = zc.cimaa.tests:OutputMetrics

.. -> src

   >>> with open('agent.cfg', 'w') as f:
   ...     f.write(src)
   >>> import os
   >>> os.mkdir('agent.d')

In addition to the testing metrics handler used here, there are
logging and Kinesis metrics handlers included in the cimaa project.

Let's create a check that generates metrics::

  [foo.txt]
  command = PY filecheck.py foo.txt

.. -> src

    >>> import sys
    >>> with open(os.path.join('agent.d', 'test.cfg'), 'w') as f:
    ...     f.write(src.replace('PY', sys.executable))

And create an agent:

    >>> import zc.cimaa.agent
    >>> agent = zc.cimaa.agent.Agent('agent.cfg')

We arrange for our monitor to provide metrics by setting the contents
of foo.txt to a JSON string:

    >>> metrics = [dict(name='speed', value=99, units='rpm'),
    ...            dict(name='loudness', value=11,
    ...                 timestamp="2014-12-13T10:28:31")]
    >>> import json
    >>> def save_metrics():
    ...     with open('foo.txt', 'w') as f:
    ...         f.write(json.dumps(dict(faults=[], metrics=metrics)))
    >>> save_metrics()

When the agent performs the check, metric data are sent to the metrics
handler:

    >>> agent.perform(0)
    2014-12-13T16:14:47.820000 //test.example.com/test/foo.txt#speed 99 rpm
    2014-12-13T10:28:31 //test.example.com/test/foo.txt#loudness 11

Thresholds
==========

We can check for allowable values of metrics by setting thresholds.

Let's add thresholds to out check definition::

  [foo.txt]
  command = PY filecheck.py foo.txt
  thresholds =
    speed warning > 50 error > 70 critical > 110 clear < 60
    loudness warning > 11 error > 20
    free ? warning <= 20 error <= 10 critical <= 3

.. -> src

    >>> with open(os.path.join('agent.d', 'test.cfg'), 'w') as f:
    ...     f.write(src.replace('PY', sys.executable))
    >>> agent = zc.cimaa.agent.Agent('agent.cfg')

Thresholds are specificied with the thresholds option.  The option has
0 or more thresholds separated by newlines.  Each threshold has a
name, and optional optional flag, and one or more parts, with each
part specifying a fault level, a criteria consisting of a comparison
operator and a value.  The special alert level ``clear`` is used to
try to avoid flapping when a value moves up and down around a level
that would cause an alert to trigger.

In the example above, for ``speed``, we'll warn if the speed gets above
50, error (and eventually alert) if above 70, and go critical (alert
immediately) if above 110.  Because we said to clear at 60, we won't
clear an alert (go from critical to warn) until speed drops below 60.

In the example above for ``free``, we see an optional flag,
``?``. Normally, if we define a threshold and don't get a value for a
metric, we error. If the ``?`` flag is used, we only check the
threshold if the metric is present.

Now, if we do checks:

    >>> agent.perform(0)
    2014-12-13T16:14:47.820000 //test.example.com/test/foo.txt#speed 99 rpm
    2014-12-13T10:28:31 //test.example.com/test/foo.txt#loudness 11

    >>> print agent.db
    {'test.example.com': [{'message': '99 > 70 (1 of 4)',
                           'name': '//test.example.com/test/foo.txt#speed',
                           'severity': 40,...

