"""Agent plugin APIs.

Note that the agent uses gevent. Plugins should work with gevent as feasible.

At least for now, no monkey-patching please.

Don't import this modult unless you have zope.interface in the path.
zc.cimaa doesn't import this module, nor does it depend on zope.interface.
"""

import zope.interface

class IDB(zope.interface.Interface):
    """Interface for recording monitoring data
    """

    def old_agents(age):
        """Return a sequence of old agents and update times

        Old agents are agents that haven't updated their faults in
        a long time.
        """

    def get_faults(agent):
        """Get previous faults for an agent.

        A sequence of dictionaries is returned.

        Faults have items:

        name
          String uniquely identifying the fault.

        severity
           An integer severity defined by Python log levels.

        message
           A message describing the fault.

        triggered (optional)
           Present and true of an alert has been triggered for the fault.

           This should be true whenever severity >= logging.CRITICAL,
           unless there's an alerting failure.

        updated
           The time the fault was last updated, as a time.time.

        since
           The time the fault was last first detected within the
           current string of failures, as a time.time.

           This must be maintained by the .
        """

    def set_faults(agent, faults):
        """Set current faults for an agent.

        See get_faults for a description of fault data.
        """

    def get_squelches(detail):
        "Return a sequence of squelch regular-expression strings"

    def get_squelch_details():
        "Return a sequence of squelch data"

    def squelch(regex, reason, user, permanent=False):
        """Add a squelch.

        The regex, reason and user arguments are strings.

        The permanent argument indicates whether the squelch should be
        kept indefinately.  A meta monitor will alert is impermanent
        squelches remain too long (e.g. more than an hours).
        """

    def unsquelch(regex):
        "Remove a squelch"

class IAlerter(zope.interface.Interface):
    """Interface for triggering and resolving alerts.
    """

    def trigger(name, message):
        """Trigger an alert with the given name(/id) and with the given message

        Note that in the case of globally-performed checks, trigger
        may be called multiple times, from different agents, for the
        same name.  It's up to the alerter to avoid messaging humans
        multiple times because of this. Pager Duty gives us this for
        free. Other alerters might employ a database to avoid
        duplicate messages. (Of course, an alerting system might
        message multiple times as part of an escallation policy.)
        """

    def resolve(self, name):
        "Resolve an alert with the given name(/id)"

class IMetrics(zope.interface.Interface):
    """Interface for handling metrics data
    """

    def __call__(timestamp, name, value, units=''):
        "Handle a single metric value"
