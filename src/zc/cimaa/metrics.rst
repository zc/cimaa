===============
Metrics support
===============

.. contents::

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

Let's add thresholds to our check definition::

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

Thresholds are specified with the thresholds option.  The option has
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

Nagios performance data
=======================

Nagios plugins can include performance data in their output::

    DISK OK - free space: / 3326 MB (56%); | /=2643MB;5948;5958;0;5968
    / 15272 MB (77%);
    /boot 68 MB (69%);
    /home 69357 MB (27%);
    /var/log 819 MB (84%); | /boot=68MB;88;93;0;98
    /home=69357MB;253404;253409;0;253414
    /var/log=818MB;970;975;0;980
    speed=0 loudness=0

.. -> src

   >>> with open('foo.txt', 'w') as f:
   ...     f.write(src)

Normally, performance data is ignored:

    >>> agent.perform(0)
    >>> print agent.db
    {'test.example.com': [{'message': 'Missing metric (2 of 4)',
                           'name': '//test.example.com/test/foo.txt#speed',
                           'severity': 40,
                           'since': 1418487287.82,
                           'updated': 1418487287.82},
                          {'message': 'Missing metric (2 of 4)',
                           'name': '//test.example.com/test/foo.txt#loudness',
                           'severity': 40,
                           'since': 1418487287.82,
                           'updated': 1418487287.82}]}

If we want parsing of performance data, we need to use the
``nagios_performance`` option in the check definition:
::

  [foo.txt]
  command = PY filecheck.py foo.txt
  nagios_performance = true
  thresholds =
    speed warning > 50 error > 70 critical > 110 clear < 60
    loudness warning > 11 error > 20
    free ? warning <= 20 error <= 10 critical <= 3

.. -> src

    >>> with open(os.path.join('agent.d', 'test.cfg'), 'w') as f:
    ...     f.write(src.replace('PY', sys.executable))
    >>> agent = zc.cimaa.agent.Agent('agent.cfg')

::

    >>> agent.perform(0)
    2014-12-13T16:14:47.820000 //test.example.com/test/foo.txt#/ 2643.0 MB
    2014-12-13T16:14:47.820000 //test.example.com/test/foo.txt#/boot 68.0 MB
    2014-12-13T16:14:47.820000 //test.example.com/test/foo.txt#/home 69357.0 MB
    2014-12-13T16:14:47.820000 //test.example.com/test/foo.txt#/var/log 818.0 MB
    2014-12-13T16:14:47.820000 //test.example.com/test/foo.txt#speed 0.0
    2014-12-13T16:14:47.820000 //test.example.com/test/foo.txt#loudness 0.0
    >>> print agent.db
    {'test.example.com': []}

Logging metrics handler
========================

To output metrics data to a Python logger, use the
``zc.cimaa.logmetrics`` metrics handler::

  [metrics]
  class = zc.cimaa.logmetrics.LogMetrics

.. test

    >>> import zc.cimaa.logmetrics, mock, json, pprint
    >>> with mock.patch('logging.getLogger') as getLogger:
    ...     handler = zc.cimaa.logmetrics.LogMetrics({})
    ...     getLogger.assert_called_with('metrics')
    ...     with mock.patch('json.dumps', side_effect=pprint.pformat):
    ...         handler('2014-12-14T17:03:26', 'speed', 42, 'dots')
    ...     print getLogger.return_value.info.call_args
    call("{'name': 'speed',\n 'timestamp': '2014-12-14T17:03:26',\n
           'units': 'dots',\n 'value': 42}")

By default, a logger named "metrics" is used, but you can supply a
different logger name with the name option.

.. test

  >>> with mock.patch('logging.getLogger') as getLogger:
  ...     handler = zc.cimaa.logmetrics.LogMetrics(dict(name='test'))
  ...     getLogger.assert_called_with('test')

Amazon Kinesis metrics handler
==============================

To send metrics data to Kinesis, use the ``zc.cimaa.kinesis``
metrics handler::

  [metrics]
  class = zc.cimaa.kinesis.Metrics
  region = us-east-1
  stream = test

.. -> src

    >>> import zc.cimaa.parser, zc.cimaa.kinesis
    >>> config = zc.cimaa.parser.parse_text(src)['metrics']
    >>> with mock.patch('boto.kinesis.connect_to_region') as connect:
    ...     handler = zc.cimaa.kinesis.Metrics(config)
    ...     connect.assert_called_with('us-east-1')
    ...     put = connect.return_value.put_record
    ...     put.return_value = dict(SequenceNumber='cn')
    ...     with mock.patch('json.dumps', side_effect=pprint.pformat):
    ...         handler('2014-12-14T17:03:26', 'speed', 42, 'dots')
    ...     print put.call_args
    ...     with mock.patch('json.dumps', side_effect=pprint.pformat):
    ...         handler('2014-12-14T17:03:26', 'speed', 42, 'dots')
    ...     print put.call_args
    call('test',
    "{'name': 'speed',\n 'timestamp': '2014-12-14T17:03:26',\n
    'units': 'dots',\n 'value': 42}",
    'speed', None, None)
    call('test',
    "{'name': 'speed',\n 'timestamp': '2014-12-14T17:03:26',\n
    'units': 'dots',\n 'value': 42}",
    'speed', None, 'cn')

In addition to the required ``region``, and ``stream`` settings, you
can supply a partition key or an explicit hash key as described in the
Amazon and boto documentation::

  [metrics]
  class = zc.cimaa.kinesis.Metrics
  region = us-east-1
  stream = test
  partition_key = 42
  explicit_hash_key = 0

.. -> src

    >>> import zc.cimaa.parser
    >>> config = zc.cimaa.parser.parse_text(src)['metrics']
    >>> with mock.patch('boto.kinesis.connect_to_region') as connect:
    ...     handler = zc.cimaa.kinesis.Metrics(config)
    ...     connect.assert_called_with('us-east-1')
    ...     put = connect.return_value.put_record
    ...     put.return_value = dict(SequenceNumber='cn')
    ...     with mock.patch('json.dumps', side_effect=pprint.pformat):
    ...         handler('2014-12-14T17:03:26', 'speed', 42, 'dots')
    ...     print put.call_args
    call('test',
    "{'name': 'speed',\n 'timestamp': '2014-12-14T17:03:26',\n
    'units': 'dots',\n 'value': 42}", '42', '0', None)

These really only matters if you have more than one shard and want to
control which shard is used.  By default, metric names are used as
partition keys, which will distribute metrics accross shards, but
arrange that the data for a single metric are in the same shard.
