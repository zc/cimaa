Agent.loop reports exceptions
=============================

Let's set up an agent::

  [agent]
  directory = agent.d
  base_interval = .1

  [database]
  class = zc.cimaa.stub:MemoryDB

  [alerter]
  class = zc.cimaa.stub:OutputAlerter

.. -> src

   >>> with open('agent.cfg', 'w') as f:
   ...     f.write(src)

   >>> import os, sys
   >>> os.mkdir('agent.d')

Create an agent:

    >>> import zc.cimaa.agent
    >>> agent = zc.cimaa.agent.Agent('agent.cfg')

Register a log handler so we can inspect what happened:

    >>> import logging
    >>> import zope.testing.loggingsupport

    >>> loghandler = zope.testing.loggingsupport.InstalledHandler(
    ...     "zc.cimaa", level=logging.WARNING)

When loop encounters a problem from perform, the exception is logged and
re-raised:

    >>> def bad_performance(minute):
    ...     raise RuntimeError("something really bad happened")

    >>> agent.perform = bad_performance

    >>> agent.loop(1)
    Traceback (most recent call last):
    RuntimeError: something really bad happened

    >>> print loghandler
    zc.cimaa.agent ERROR
      calling perform from loop:


Clean up:

    >>> agent.clear()
    >>> loghandler.uninstall()
