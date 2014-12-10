import grequests
import json

api_url = 'https://events.pagerduty.com/generic/2010-04-15/create_event.json'

class PagerDutyCallFailed(Exception):
    pass

class Alerter:

    def __init__(self, config):
        self.headers = {
            'Authorization': 'Token token=%s' % config['token'],
            'Content-Type': 'application/json',
            }
        self.service = config['service']

    def _event(self, event_type, name, description):
        resp = grequests.post(
            api_url,
            data = json.dumps(dict(
                service_key = self.service,
                incident_key = name,
                event_type = event_type,
                description = description,
                )),
            headers = self.headers,
            ).send()
        if resp.status_code != 200:
            raise PagerDutyCallFailed(resp.content)

    def _broken(self, name):
        return ' '.join(name[2:].split('/', 2))

    def trigger(self, name, message):
        self._event('trigger', name, "%s\n%s" % (self._broken(name), message))

    def resolve(self, name):
        friendly_name = ' '.join(name[2:].split('/', 2))
        self._event('resolve', name, "Cleared: %s" % self._broken(name))
