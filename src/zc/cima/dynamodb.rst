Storing monitoring data in DynamoDB
===================================

You can store your monitoring data in dynamodb using the
``zc.cima.dynamodb`` implementation in your agent configuration::

  [database]
  class = zc.cima.dynamodb
  region = us-east-1

Additional configuration options:

prefix
  A table name prefix, defaulting to ``cima``.  The tables used will
  have names prefixed with this string and a dot (e.g. ``cima.agents``).

aws_access_key_id and aws_secret_access_key
  Use these to specify keys in the configuration. If not specified,
  then credentials will be searched for in environment variables,
  ~/.boto and instance credentials.

There are helper scripts for setting up dynamodb tables, and for setting
and unsetting squelches.  To use these, we need to set up a configuration
file::

  [database]
  class = zc.cima.dynamodb
  region = us-east-1
  prefix = test

.. -> src

    >>> import os, random, pkg_resources

    >>> with open('conf', 'w') as f:
    ...     f.write(src.replace('us-east-1', os.environ['DYNAMO_TEST'])
    ...               .replace('test', 'test%s' % random.randint(0,999999999))
    ...               )

    >>> setup = pkg_resources.load_entry_point(
    ...     'zc.cima', 'console_scripts', 'setup-dynamodb')

We call the setup script, passing the name of the configuration file.

    >>> setup(['conf'])

We'll use the squelch script to add a squelch:

    >>> squelch = pkg_resources.load_entry_point(
    ...      'zc.cima', 'console_scripts', 'squelch-dynamodb')
    >>> import mock
    >>> with mock.patch('getpass.getuser', return_value='tester'):
    ...     squelch(['conf', 'test', 'testing'])

Let's set up a database object.

    >>> import zc.cima.dynamodb
    >>> db = zc.cima.dynamodb.DB(zc.cima.dynamodb.config_parse('conf'))

And perform some operations:

    >>> db.set_faults('agent', [])
    >>> [atime] = [a['updated'] for a in db.dump('agents')]
    >>> db.get_faults('agent')
    []

    >>> db.get_squelches()
    [u'test']

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
    ...     ])

The agent time isn't updated when we save faults:

    >>> [atime] == [a['updated'] for a in db.dump('agents')]
    True

    >>> pprint(db.dump())
    {'agents': [{u'name': u'agent',
                 u'updated': Decimal('1418068819.8888809680938720703125')}],
     'faults': [{u'agent': u'agent',
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

    >>> pprint(db.get_faults('agent'))
    [{u'agent': u'agent',
      u'message': u'f2 is bad',
      u'name': u'f2',
      u'severity': Decimal('40')},
     {u'agent': u'agent',
      u'message': u'f3 is bad',
      u'name': u'f3',
      u'severity': Decimal('50'),
      u'triggered': u'y'}]
    >>> db.set_faults('agent', [])

    >>> [atime] < [a['updated'] for a in db.dump('agents')]
    True

    >>> squelch(['conf', 'test', '-r'])
    >>> pprint(db.dump())
    {'agents': [{u'name': u'agent',
                 u'updated': Decimal('1418068821.55653095245361328125')}],
     'faults': [],
     'squelches': []}


Cleanup:

    >>> for table in zc.cima.dynamodb.schemas:
    ...     _ = getattr(db, table).delete()
