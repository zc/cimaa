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

There are helper scripts for setting up dynamodb tables, and for setting
and unsetting squelches.  To use these, we need to set up a configuration
file::

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

We'll use the squelch script to add a squelch:

    >>> squelch = pkg_resources.load_entry_point(
    ...      'zc.cimaa', 'console_scripts', 'squelch-dynamodb')
    >>> import mock
    >>> with mock.patch('getpass.getuser', return_value='tester'):
    ...     squelch(['conf', 'test', 'testing'])

Let's set up a database object.

    >>> import zc.cimaa.dynamodb
    >>> db = zc.cimaa.dynamodb.DB(zc.cimaa.dynamodb.config_parse('conf'))

And perform some operations:

    >>> db.set_faults('agent', [])
    >>> db.get_faults('agent')
    []

    >>> db.get_squelches()
    [u'test']
    >>> pprint(db.get_squelch('test'))
    {u'reason': u'testing',
     u'regex': u'test',
     u'time': Decimal('1420294404.0289080142974853515625'),
     u'user': u'tester'}

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
                 u'name': u'agent',
                 u'updated': Decimal('1418160088.916944026947021484375')},
                {u'agent': u'agent',
                 u'name': u'blank',
                 u'severity': T},
                {u'agent': u'agent',
                 u'message': u'f2 is bad',
                 u'name': u'f2',
                 u'severity': Decimal('40')},
                {u'agent': u'agent',
                 u'message': u'f3 is bad',
                 u'name': u'f3',
                 u'severity': Decimal('50'),
                 u'triggered': u'y'}],
     'squelches': [{u'reason': u'testing',
                    u'regex': u'test',
                    u'time': Decimal('1418068818.7642829418182373046875'),
                    u'user': u'tester'}]}

Notice that the faults data includes data for an agent '_'. This is
heartbeat data that tells us when the agent last ran.  We can use this
to find old agents:

    >>> db.old_agents(900) # agents that haven't run in 15 minutes
    []
    >>> pprint(db.old_agents(0))
    [{'name': u'agent',
      'updated': Decimal('1418160088.916944026947021484375')}]

    >>> pprint(db.get_faults('agent'))
    [{u'agent': u'agent',
      u'message': u'',
      u'name': u'blank',
      u'severity': T},
     {u'agent': u'agent',
      u'message': u'f2 is bad',
      u'name': u'f2',
      u'severity': Decimal('40')},
     {u'agent': u'agent',
      u'message': u'f3 is bad',
      u'name': u'f3',
      u'severity': Decimal('50'),
      u'triggered': u'y'}]
    >>> db.set_faults('agent', [])

    >>> squelch(['conf', 'test', '-r'])
    >>> pprint(db.dump())
    {'faults': [{u'agent': u'_',
                 u'name': u'agent',
                 u'updated': Decimal('1418160089.4438440799713134765625')}],
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
      u'severity': Decimal('50')}]


Cleanup:

    >>> for table in zc.cimaa.dynamodb.schemas:
    ...     _ = getattr(db, table).delete()
