"""Agent plugin APIs.

Note that the agent uses gevent. Plugins should work with gevent as feasible.

At least for now, no monkey-patching please.

Don't import this modult unless you have zope.interface in the path.
zc.cima doesn't import this module, nor does it depend on zope.interface.
"""

import zope.interface

class IDB(zope.interface.Interface):
    """Interface for recording monitoring data
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

    def get_squelches():
        "Return a sequence of squelch regular expressions."

    def squelch(regex, reason, user):
        """Add a squelch.

        All arguments are strings.
        """

    def unsquelch(regex):
        "Remove a squelch"

class IAlerter(zope.interface.Interface):
    """Interface for triggering and resolving alerts.
    """

    def trigger(name, message):
        "Trigger an alert with the given name(/id) and with the given message"

    def resolve(self, name):
        "Resolve an alert with the given name(/id)"
