=================
Slack API Alerter
=================

The ``zc.cimaa.slack.Alerter`` class implements the Alerter interface using the
`Slack.com API <https://api.slack.com>`_.

This test takes the Slack API token from the environment variable
``SLACK_TOKEN``.  If there's an environment variable ``SLACK_CHANNEL`` we'll
use that channel, otherwise we default to ``general``. The variables that are
set up for us are::

    token:          The API token
    channel:        The channel name used for test messages
    channel_id:     The Slack ID of the named channel (Used for test
                    validation)

(You can find a Slack API token in the `Slack documentation
<https://api.slack.com/web>`_. Under Authentication it will either show a token
if you've created one or provide an option to generate one.)

We'll also use the slack API to validate our tests::

    >>> import slacker
    >>> slack = slacker.Slacker(token)

First, we scan messages and get a timestamp to mark when we start::

    >>> msgs = slack.channels.history(channel_id, count=1)
    >>> assert msgs.successful
    >>> ts = msgs.body['messages'][-1]['ts']

Now we create an Alerter::

    >>> import zc.cimaa.slack
    >>> alerter = zc.cimaa.slack.Alerter(
    ...     dict(token = token,
    ...          channel = channel,
    ...     )
    ... )

Trigger an alert::

    >>> alerter.trigger(name='//test.example.com/doctest',
    ...     message="Ouch!")

Resolve an alert::

    >>> alerter.resolve(name='//test.example.com/doctest')

Then retreive newer messages from slack::

    >>> msgs = slack.channels.history(channel_id, oldest=ts)

    >>> my_msgs = [x for x in msgs.body ['messages']
    ...             if x['subtype'] == 'bot_message']
    >>> assert len(my_msgs) == 2
    >>> [alert] = [msg for msg in my_msgs if 'Alert' in msg['text']]
    >>> [clear] = [msg for msg in my_msgs if 'Clear' in msg['text']]

    >>> pprint(alert)
    {u'subtype': u'bot_message',
     u'text': u'_*Alert*_: *<http://test.example.com|test.example.com> doctest*: Ouch!',
     u'ts': u'...',
     u'type': u'message',
     u'username': u'cimaa'}

    >>> pprint(clear)
    {u'subtype': u'bot_message',
     u'text': u'*Clear*: *<http://test.example.com|test.example.com> doctest*',
     u'ts': u'...',
     u'type': u'message',
     u'username': u'cimaa'}
