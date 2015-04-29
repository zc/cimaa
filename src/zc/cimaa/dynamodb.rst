Storing monitoring data in DynamoDB
===================================

You can store your monitoring data in dynamodb using the
``zc.cimaa.dynamodb`` implementation in your agent configuration::

  [database]
  class = zc.cimaa.dynamodb
  region = us-east-1

Additional configuration options:

prefix
  A table name prefix, defaulting to ``cimaa``.  The tables used will
  have names prefixed with this string and a dot (e.g. ``cimaa.agents``).

aws_access_key_id and aws_secret_access_key
  Use these to specify keys in the configuration. If not specified,
  then credentials will be searched for in environment variables,
  ~/.boto and instance credentials.

There is a helper script for setting up dynamodb table.  To use this,
we need to set up a configuration file::

  [database]
  class = zc.cimaa.dynamodb
  region = us-east-1
  prefix = test

.. -> src

    >>> import os, random, pkg_resources

    >>> with open('conf', 'w') as f:
    ...     f.write(src.replace('us-east-1', os.environ['DYNAMO_TEST'])
    ...               .replace('test', 'test%s' % random.randint(0,999999999))
    ...               )

    >>> setup = pkg_resources.load_entry_point(
    ...     'zc.cimaa', 'console_scripts', 'setup-dynamodb')

We call the setup script, passing the name of the configuration file.

    >>> setup(['conf'])

Let's set up a database object.

    >>> import zc.cimaa.dynamodb
    >>> db = zc.cimaa.dynamodb.DB(zc.cimaa.dynamodb.config_parse('conf'))

And perform some operations:

    >>> db.squelch('test', 'testing', 'tester', True)
    >>> db.squelch('.', 'testing global', 'deployer')
    >>> db.set_faults('agent', [])
    >>> db.get_faults('agent')
    []

    >>> db.get_squelches()
    [u'.', u'test']
    >>> pprint(db.get_squelch_details())
    [{u'permanent': False,
      u'reason': u'testing global',
      u'regex': u'.',
      u'time': 1420294404,
      u'user': u'deployer'},
     {u'permanent': True,
      u'reason': u'testing',
      u'regex': u'test',
      u'time': 1420294404,
      u'user': u'tester'}]

    >>> db.set_faults('agent', [
    ...     dict(name='f1', severity=40, message='f1 is bad'),
    ...     ])

    >>> db.set_faults('agent', [
    ...     dict(name='f1', severity=40, message='f1 is bad'),
    ...     dict(name='f2', severity=40, message='f2 is bad'),
    ...     ])

    >>> db.set_faults('agent', [
    ...     dict(name='f3', severity=50, message='f3 is bad', triggered='y'),
    ...     dict(name='f2', severity=40, message='f2 is bad'),
    ...     dict(name='blank', severity=50, message=''),
    ...     ])

    >>> pprint(db.dump())
    {'faults': [{u'agent': u'_',
                 u'message': u'',
                 u'name': u'agent',
                 u'updated': 1418160088},
                {u'agent': u'agent',
                 u'message': u'',
                 u'name': u'blank',
                 u'severity': 50,
                 u'since': T},
                {u'agent': u'agent',
                 u'message': u'f2 is bad',
                 u'name': u'f2',
                 u'severity': 40,
                 u'since': T},
                {u'agent': u'agent',
                 u'message': u'f3 is bad',
                 u'name': u'f3',
                 u'severity': 50,
                 u'since': T,
                 u'triggered': u'y'}],...

Notice that the faults data includes data for an agent '_'.  This is
heartbeat data that tells us when the agent last ran.  We can use this
to find agents that no longer report:

    >>> db.old_agents(900) # agents that haven't run in 15 minutes
    []
    >>> pprint(db.old_agents(0))
    [{'name': u'agent',
      'updated': 1418160088}]

    >>> pprint(db.get_faults('agent'))
    [{u'agent': u'agent',
      u'message': u'',
      u'name': u'blank',
      u'severity': 50,
      u'since': T},
     {u'agent': u'agent',
      u'message': u'f2 is bad',
      u'name': u'f2',
      u'severity': 40,
      u'since': T},
     {u'agent': u'agent',
      u'message': u'f3 is bad',
      u'name': u'f3',
      u'severity': 50,
      u'since': T,
      u'triggered': u'y'}]
    >>> db.set_faults('agent', [])

    >>> db.unsquelch('.')
    >>> db.unsquelch('test')
    >>> pprint(db.dump())
    {'faults': [{u'agent': u'_',
                 u'message': u'',
                 u'name': u'agent',
                 u'updated': 1418160089}],
     'squelches': []}

DynamoDB does not return keys for empty string values. The DB implementation
has to ensure that it gets restored to avoid KeyErrors::

    >>> db.set_faults('agent', [
    ...     dict(name='blank', severity=50, message=''),
    ...     ])
    >>> pprint(db.get_faults('agent'))
    [{u'agent': u'agent',
      u'message': u'',
      u'name': u'blank',
      u'severity': 50,
      u'since': T}]

The remove_agent method is used to remove an agent from the database
completely; both faults and the heartbeat record are removed, while
records for other agents are not touched:

    >>> db.set_faults('tnega', [
    ...     dict(name='f1', severity=40, message='f1 is bad'),
    ...     dict(name='f2', severity=40, message='f2 is bad'),
    ...     ])

    >>> db.remove_agent('agent')
    >>> pprint(db.dump())
    {'faults': [{u'agent': u'_',
                 u'message': u'',
                 u'name': u'tnega',
                 u'updated': T},
                {u'agent': u'tnega',
                 u'message': u'f1 is bad',
                 u'name': u'f1',
                 u'severity': 40,
                 u'since': T},
                {u'agent': u'tnega',
                 u'message': u'f2 is bad',
                 u'name': u'f2',
                 u'severity': 40,
                 u'since': T}],
     'squelches': []}


Exceeding provisioned throughput
--------------------------------

It's possible to exceed provisioned throughput with DynamoDB; if this
happens on a regular basis during operation, the best thing to do is
increased the provisioned throughput, but sometimes it's safe to
consider a transient condition.  This has been observed when restarting
many agents at once; the reads required for each agent to get their own
state can easily exceed the allowed throughput.  In this case, trying
again after a brief wait is acceptable.

To deal with this, we want to ensure the throughput-exceeded events are
tracked to allow an operations team (or a monitor) to determine the
frequency of these events, but we don't want to cease operation.

The throughput throttle can be triggered on either reads of writes;
we'll look at the handling of each of these separately.

    >>> from boto.dynamodb2.exceptions import (
    ...     ProvisionedThroughputExceededException,
    ...     )
    >>> import boto.dynamodb2.exceptions
    >>> import boto.dynamodb2.table
    >>> import mock
    >>> import zc.cimaa.dynamodb

We'll want a side-effect that raises the appropriate exception for a
specified number of times before allowing the operation to succeed:

    >>> class State(object):
    ...     n = 0

    >>> def throttled(cls, name, ntries):
    ...     tries = []
    ...     real_method = getattr(cls, name)
    ...     def tryit(*args, **kw):
    ...         tries.append(0)
    ...         if len(tries) > ntries:
    ...             # Do the real thing
    ...             return real_method(*args, **kw)
    ...         else:
    ...             raise ProvisionedThroughputExceededException(
    ...                 400, "too many requests")
    ...     return mock.patch.object(
    ...         cls, name, autospec=True, side_effect=tryit)

We'll also want a loghandler:

    >>> import logging
    >>> import zope.testing.loggingsupport

    >>> loghandler = zope.testing.loggingsupport.InstalledHandler(
    ...     "zc.cimaa", level=logging.WARNING)


Throttled reads
~~~~~~~~~~~~~~~

If reads are throttled, we'll make a few additional attempts to read the
data:

    >>> db.last_faults.clear()

    >>> with throttled(boto.dynamodb2.table.Table, "query_2", 2):
    ...     db.get_faults("agent")
    []

    >>> print loghandler
    zc.cimaa.dynamodb ERROR
      hit dynamodb throughput limit (reading)
    zc.cimaa.dynamodb WARNING
      exceeded provisioned throughput; waiting 4.23542 seconds
    zc.cimaa.dynamodb ERROR
      hit dynamodb throughput limit (reading)
    zc.cimaa.dynamodb WARNING
      exceeded provisioned throughput; waiting 0.2344 seconds

    >>> loghandler.clear()

We won't wait forever, though; if it's that bad, we'll still fail:

    >>> with throttled(boto.dynamodb2.table.Table, "query_2",
    ...                zc.cimaa.dynamodb.READ_ATTEMPTS):
    ...     db.get_faults("agent")
    Traceback (most recent call last):
    RuntimeError: error reading dynamodb in 5 tries

    >>> print loghandler
    zc.cimaa.dynamodb ERROR
      hit dynamodb throughput limit (reading)
    zc.cimaa.dynamodb WARNING
      exceeded provisioned throughput; waiting 7.75477721994 seconds
    zc.cimaa.dynamodb ERROR
      hit dynamodb throughput limit (reading)
    zc.cimaa.dynamodb WARNING
      exceeded provisioned throughput; waiting 0.394166737729 seconds
    zc.cimaa.dynamodb ERROR
      hit dynamodb throughput limit (reading)
    zc.cimaa.dynamodb WARNING
      exceeded provisioned throughput; waiting 8.95004687846 seconds
    zc.cimaa.dynamodb ERROR
      hit dynamodb throughput limit (reading)
    zc.cimaa.dynamodb WARNING
      exceeded provisioned throughput; waiting 7.63829566361 seconds
    zc.cimaa.dynamodb ERROR
      hit dynamodb throughput limit (reading); no more attempts

    >>> loghandler.clear()


Throttled writes
~~~~~~~~~~~~~~~~

We'll also make repeated attempts to write to DynamoDB:

    >>> with throttled(boto.dynamodb2.table.BatchTable, "put_item", 2):
    ...     db.set_faults("agent", [])

    >>> print loghandler
    zc.cimaa.dynamodb ERROR
      hit dynamodb throughput limit (writing)
    zc.cimaa.dynamodb WARNING
      exceeded provisioned throughput; waiting 4.23542 seconds
    zc.cimaa.dynamodb ERROR
      hit dynamodb throughput limit (writing)
    zc.cimaa.dynamodb WARNING
      exceeded provisioned throughput; waiting 0.2344 seconds

    >>> loghandler.clear()

As with reads, we won't wait forever:

    >>> with throttled(boto.dynamodb2.table.BatchTable, "put_item",
    ...                zc.cimaa.dynamodb.WRITE_ATTEMPTS):
    ...     db.set_faults("agent", [])
    Traceback (most recent call last):
    RuntimeError: error writing dynamodb in 3 tries

    >>> print loghandler
    zc.cimaa.dynamodb ERROR
      hit dynamodb throughput limit (writing)
    zc.cimaa.dynamodb WARNING
      exceeded provisioned throughput; waiting 4.23542 seconds
    zc.cimaa.dynamodb ERROR
      hit dynamodb throughput limit (writing)
    zc.cimaa.dynamodb WARNING
      exceeded provisioned throughput; waiting 0.2344 seconds
    zc.cimaa.dynamodb ERROR
      hit dynamodb throughput limit (writing); no more attempts

    >>> loghandler.clear()

Cleanup:

    >>> loghandler.uninstall()

    >>> for table in zc.cimaa.dynamodb.schemas:
    ...     _ = getattr(db, table).delete()
