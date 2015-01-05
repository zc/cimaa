import argparse
import json
import logging
import sys
import time
import urllib
import zc.cimaa.parser

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description='Perform meta-monitoring checks')
    parser.add_argument('configuration',
                        help='agent configuration file')
    parser.add_argument(
        '--warn', '-w', type=int, default=2,
        help='Age, in agent intervals, to warn of old agents')
    parser.add_argument(
        '--error', '-e', type=int, default=5,
        help='Age, in agent intervals, to error on old agents')
    parser.add_argument(
        '--global-squelch-age', '-s', type=int, default=60,
        help='Maximum age, in minutes, of global squelches')

    args = parser.parse_args(args)
    config = zc.cimaa.parser.parse_file(args.configuration)
    db = zc.cimaa.parser.load_handler(config['database'])
    agent = config.get('agent', {})
    base_interval = int(agent.get('base_interval', 60))

    warn = args.warn * base_interval
    error = args.error * base_interval
    max_squelch = args.global_squelch_age * 60

    faults = []
    result = dict(faults=faults)
    now = time.time()

    # Check for inactive agents:
    for agent in sorted(db.old_agents(warn), key=agent_name):
        age = now - agent['updated']
        faults.append(dict(
            name=agent['name'],
            message='Inactive agent',
            severity=logging.ERROR if age > error else logging.WARNING,
            ))

    # Check for forgotten global squelch
    old_squelches = []
    for squelch in db.get_squelch_details():
        if squelch['permanent']:
            continue
        age = now - squelch['time']
        if age > max_squelch:
            faults.append(dict(
                name='squelch-' + urllib.quote(squelch['regex']),
                message='Alerts squelched %d minutes ago by %s because %s' % (
                    age / 60, squelch['user'], squelch['reason']),
                severity=logging.ERROR,
                ))
    print json.dumps(result)

def agent_name(agent):
    return agent['name']
