Squelch script
==============

There are helper scripts for adding and removing squelches.

    >>> import pkg_resources
    >>> squelch = pkg_resources.load_entry_point(
    ...     'zc.cimaa', 'console_scripts', 'squelch')
    >>> unsquelch = pkg_resources.load_entry_point(
    ...     'zc.cimaa', 'console_scripts', 'unsquelch')

You need to pass an agent configuration file to the scripts::

  [database]
  class = zc.cimaa.tests:MetaDB

.. -> src

    >>> with open('agent.cfg', 'w') as f:
    ...     f.write(src)

To add a squelch:

    >>> squelch('agent.cfg -p test testing'    .split())
    >>> squelch('agent.cfg     . deploying'    .split())

When run under **sudo**, the user's real identity is reflected if available:

    >>> import mock
    >>> import os

    >>> os.environ["SUDO_USER"] = "sudotester"

    >>> with mock.patch('getpass.getuser', side_effect=(lambda: "root")):
    ...     squelch('agent.cfg  im-sudo iwanna'    .split())

    >>> del os.environ["SUDO_USER"]

    >>> import zc.cimaa.tests
    >>> pprint(zc.cimaa.tests.meta_db.squelches)
    {'.': {'permanent': False,
           'reason': 'deploying',
           'time': 1417968068.01,
           'user': 'tester'},
     'im-sudo': {'permanent': False,
              'reason': 'iwanna',
              'time': 1417968068.01,
              'user': 'sudotester'},
     'test': {'permanent': True,
              'reason': 'testing',
              'time': 1417968068.01,
              'user': 'tester'}}

To remove a squelch:

    >>> unsquelch('agent.cfg test'       .split())
    >>> unsquelch('agent.cfg    .'       .split())
    >>> unsquelch('agent.cfg im-sudo'    .split())
    >>> zc.cimaa.tests.meta_db.squelches
    {}
