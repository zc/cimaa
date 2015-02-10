"""Stub plugin implementations for testing and debugging
"""
import gevent
import json
import pprint
import time

class MemoryDB:

    def __init__(self, config):
        self.faults = json.loads(config.get('faults', '{}'))
        self.squelches = {}
        self.agents = {}

    def old_agents(self, age):
        max_updated = time.time() - age
        return [dict(name=k, updated=v) for k, v in self.agents.items()
                if v < max_updated]

    def get_faults(self, agent):
        return self.faults.get(agent, ())

    def set_faults(self, agent, faults, now=None):
        times = {
            f[name]: f['since']
            for f in self.faults.get('agent', ()) if f['name']
            }
        for f in faults:
            f['since'] = times.get(f['name'], f['updated'])
        self.faults[agent] = faults
        self.agents[agent] = now or time.time()

    def get_squelches(self):
        return sorted(self.squelches)

    def get_squelch_details(self):
        return [_squelch_detail(item)
                for item in sorted(self.squelches.items())]

    def squelch(self, regex, reason, user, permanent=False, now=None):
        self.squelches[regex] = dict(
            reason = reason,
            user = user,
            time = now or 1417968068.01,
            permanent = permanent,
            )

    def unsquelch(self, regex):
        del self.squelches[regex]

    def remove_agent(self, agent):
        if agent in self.agents:
            del self.agents[agent]
        if agent in self.faults:
            del self.faults[agent]

    def __str__(self):
        return pprint.pformat(self.faults)

def _squelch_detail((regex, data)):
    data = data.copy()
    data['regex'] = regex
    return data


class OutputAlerter:

    nfail = 0
    sleep = 0.0

    def __init__(self, config):
        pass

    def fail(self):
        if self.nfail > 0:
            self.nfail -= 1
            raise ValueError('fail')
        gevent.sleep(self.sleep)

    def log(self, *args):
        print self.__class__.__name__, ' '.join(args)

    def trigger(self, name, message):
        self.fail()
        self.log('trigger', name, message)

    def resolve(self, name):
        self.fail()
        self.log('resolve', name)

def OutputMetrics(config):
    def output_metrics(timestamp, name, value, units=''):
        print timestamp, name, value, units
    return output_metrics
