
import ConfigParser
import gevent.subprocess
import json
import logging
import os
import re
import socket
import time

logger = logging.getLogger(__name__)

status_codes = [
    logging.INFO, logging.WARNING, logging.ERROR, logging.ERROR]

class Agent:

    def __init__(self, config):
        parser = ConfigParser.RawConfigParser()
        parser.read(config)
        options = dict(parser.items('agent'))
        aname = self.name = options.get('name', socket.getfqdn())
        self.timeout = float(options.get('timeout', 40))

        db = self.db = load_handler(parser, 'database')
        db.heartbeat(aname, 'start')

        alerter = self.alerter = load_handler(parser, 'alerter')

        directory = options['directory']
        self.checks = checks = []
        for name in os.listdir(directory):
            if name.endswith('.cfg'):
                cparser = ConfigParser.RawConfigParser()
                cparser.read(os.path.join(directory, name))
                fname = name[:-4]
                for section in cparser.sections():
                    config = dict(cparser.items(section))
                    interval = int(config.pop('interval', 1))
                    retry_interval = int(config.pop('retry_interval', 1))
                    retry = int(config.pop('retry', 3))
                    command = config['command']
                    if not section.startswith('//'):
                        section = '//%s/%s/%s' % (aname, fname, section)
                    checks.append(Check(section, command,
                                        interval, retry, retry_interval))

    critical = {}
    def perform(self):
        # start checks. XXX maybe we want to limit the number of checks
        # running at once.
        self.heartbeat('performing')
        checklets = [(check, gevent.spawn(check.perform))
                     for check in self.checks]

        deadline = time.time() + self.timeout
        faults = []
        for check, checklet in checklets:
            timeout = max(0, deadline - time.time())
            checklet.join(timeout)
            self.heartbeat('checking '+check.name)
            cresults = checklet.value
            if cresults is None:
                checklet.kill(block=False)
                faults.append(monitor_error(
                    'timeout', prefix=check.name+'#',
                    severity=logging.CRITICAL))
            else:
                for f in cresults.get('faults', ()):
                    if f.get('name', ''):
                        f['name'] = check.name + '#' + f['name']
                    else:
                        f['name'] = check.name
                    faults.append(f)

        self.db.set_faults(self.name, faults)

        critical = {}
        squelches = None
        for f in faults:
            if f['severity'] < logging.CRITICAL:
                continue
            if squelches is None:
                squelches = self.db.get_squelches()
            for squelch in squelches:
                if re.search(squelch, f['name']):
                    break
            else:
                critical[f['name']] = f['message']

        if critical != self.critical:
            self.heartbeat('triggering')
            self.db.alert_start(self.name)
            for name, message in critical.items():
                if self.critical.get(name, None) != message:
                    self.alerter.trigger(name, message)
            for name in self.critical:
                if name not in critical:
                    self.alerter.resolve(name)
            self.critical = critical
            self.db.alert_finished(self.name)

        self.heartbeat('performed')

    def heartbeat(self, label):
        self.db.heartbeat(self.name, label)

class Check:

    failures = 0
    last_check = 0

    def __init__(self, name, command, interval, retry, retry_interval):
        self.name = name
        self.command = command
        self.interval = interval
        self.retry = retry
        self.chances = retry + 1
        self.retry_interval = retry_interval

    def perform(self):
        try:
            proc = gevent.subprocess.Popen(
                self.command,
                stdout=gevent.subprocess.PIPE,
                stderr=gevent.subprocess.PIPE,
                shell=True)
            try:
                stdout, stderr = proc.communicate()
            except gevent.GreenletExit:
                proc.kill()
                raise

            status = proc.returncode

            if status == 0 and stdout.startswith('{'):
                try:
                    result = json.loads(stdout)
                    for f in result['faults']:
                        if isinstance(f['severity'], basestring):
                            f['severity'] = severity_names[
                                f['severity'].lower()]
                        f['message']
                except Exception, v:
                    logger.exception("Bad json response for %s", self.name)
                    result = dict(faults=[dict(
                        name='json-error',
                        message = "%s: %s" % (v.__class__.__name__, v),
                        severity = logging.CRITICAL,
                        )])
            else:
                failures = []
                result = dict(faults=failures)

                if stderr:
                    failures.append(monitor_error("stderr", stderr))

                stdout = stdout or stderr
                if not stdout:
                    failures.append(monitor_error("no-out"))
                    stdout = "(no output)"
                if len(stdout) > 200:
                    stdout = stdout[:200]+' ...'

                if status < 4:
                    if status:
                        failures.append(dict(severity=status_codes[status],
                                             message=stdout))
                else:
                    failures.append(monitor_error("status", stdout))
                    status = logging.CRITICAL

            # handle soft errors
            errors = [f for f in result.get('faults', ())
                      if logging.ERROR <= f['severity'] < logging.CRITICAL]
            if errors:
                self.failures += 1
                if self.failures > self.retry:
                    for f in errors:
                        f['severity'] = logging.CRITICAL
                else:
                    for f in errors:
                        f['message'] = f.get('message', '') + " (%s of %s)" % (
                            self.failures, self.chances)
            else:
                self.failures = 0

            return result
        except Exception, v:
            logger.exception("Checker failed %s", self.name)
            result = dict(faults=[dict(
                name='checker',
                message = "%s: %s" % (v.__class__.__name__, v),
                severity = logging.CRITICAL,
                )])

severity_names = dict(warning=30, error=40, critical=50)

def monitor_error(name, message='', prefix='', severity=logging.ERROR):
    return dict(name=prefix+'monitor-'+name, message=message, severity=severity)

def load_handler(parser, name):
    config = dict(parser.items(name))
    mod, name = config['class'].split(':')
    mod = __import__(mod, {}, {}, [name])
    return getattr(mod, name)(config)
