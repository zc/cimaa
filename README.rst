Coordinating Independent Monitoring Agent Architecture (CIMAA)
**************************************************************

.. contents::

We were looking for a monitoring solution that could replace our
previous in-house system, which replaces Nagios. Certain
characteristics were very important to us:

- Support metrics and faults

- Simplicity

  We wanted a solution that was easy to manage.  Many monitoring
  systems require maintenance of infrastructure, like message busses,
  databases, or special coordinators.

- Distributed

  - Distributed configuration

    Our automation is geared toward self-contained applications that
    are in charge of all aspects of their configuration, including
    monitoring.

    When an application is deployed to a host, it should be able to
    easily implement local monitoring configuration.

  - Distributed checks

    Checks are spread over hosts being monitored.  A common pitfall
    with Nagios is that a central monitoring host can't keep up with
    all of the tests it needs to perform.

  - No mother ship. Many distributes systems use a centralized
    coordinator, which creates a single point of failure and a source
    of complexity.

- Flexibility

  It should be easy to choose monitoring infrastructure to suit your
  environment.

- Nagios (and nagionic) plugin support

  Something we think Nagios got right is using separate programs to
  perform checks. This makes debugging checks very easy and allows
  checks to be implemented in a variety of ways.

  We wanted to be able to leverage existing plugins as well as build
  on the simplicity of using external programs to implement checks.

- Application monitoring with Docker support

  Monitoring of our applications is as important to us as system
  monitoring.  A common approach to this is to provide a monitoring
  interface in running services that can be used to access monitoring
  information. This is especially important when using Docker, because
  it allows a monitoring agent to just access a port exposed by a
  container, rather than breaking encapsulation with external
  monitoring scripts.

We shopped and failed to find an existing system that addressed our
needs.  Maybe we would have found something eventually, but we
realized that will less effort than it would take to find and
integrate what we needed, we could build something very simple.

We'd built an in-house system before, which while satisfying some of
the requirements above, still fell short and was more complicated than
what we were comfortable maintaining over the long run.  Experience
with this system and with Nagios earlier informed out requirements and
our approach.

Architectural overview
**********************

A CIMAA system consists of one or more agents spread over each machine
we control. Generally, each agent is only responsible for checking the
machine it runs on.

Agents
======

- Store heartbeat and fault information in a database. The database is
  pluggable.  The first implementation is for DynamoDB.

- Use pluggable alerters to notify about critical faults.  An initial
  implementation supports PagerDuty.

- Use pluggable metrics sinks.  Initial implementations include logs
  (log files, syslog-ng, etc.) and Kinesis.

Checks
======

- Configured locally

- Nagios plugins

- CIMAA plugins

  Stand-alone programs that output JSON fault and metric data.

- Network checks

  TCP addresses or unix-domain sockets that output JSON fault and
  metric data.

- Simple network tests:

  - Can an address be connected to.

  - simple HTTP checks with url, expected status code and maybe
    expected text content.

Meta checks
===========

- Check whether agents are running (using hearbeats) and whether
  notifications are working.

  If notification failures are detected, can notify operations staff
  over secondary or tertiary channels.

  Alert if global squelch has been in place too long.

- Run as ordinary checks on many or all agents.

- Avoids need for mother ship.

We'll need to put some thought into strategies and support for
avoiding thundering herds.

Squelches
=========

- Patterns stored in database to prevent notifications of critical
  errors for faults with names matching the patterns.

  (Currently, regular expressions, but maybe these should be less
  powerful.)

- Can be used in cases where you only want to alert when there are
  faults on multiple hosts for a service. In this case, squelch
  host-specific alerts and implement a meta-monitor that uses data
  from multiple hosts.

Status
******

We're still building.

Done
====

- Initial agent implementation with:

  - support for Nagios and CIMAA plugins.

  - faults

  - database

  - alerts

  - Metric support

    - metrics outout

    - metric-threshold checks

    - logging back-end

    - Kinesis back-end

- DynamoDB database implementation

- PagerDuty alerter implementation.

To do
=====

- Web front end to view current faults and squelches and to manage squelches.

- Meta checks

- Network checks

- Production use

- Packaging

- Maybe database configuration of checks to be performed everywhere.


Changes
*******

0.1.0 (yyyy-mm-dd)
==================

Initial release
