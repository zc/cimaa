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

        A list of dictionaries is returned.

        Faults have items:

        name
          String uniquely identifying the fault.

        severity
           An integer severity defined by Python log levels.

        message
           A message describing the fault.

        updated (not yet implemented)
           The time the fault was last updated, as a time.time.

        since (not yet implemented)
           The time the fault was last first detected within the
           current string of failures, as a time.time.
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

    The methods return joinables (e.g. greenlets), which jave a ``join``
    method and ``value`` and ``exception`` attributes as defined by greenlets.
    """

    def trigger(name, message):
        """Trigger an alert with the given name(/id) and with the given message

        Returns a joinable.
        """

    def resolve(self, name):
        """Resolve an alert with the given name(/id)

        Returns a joinable.
        """
