import ConfigParser
import argparse
import gevent.subprocess
import json
import logging
import os
import re
import socket
import sys
import time

logger = logging.getLogger(__name__)

status_codes = [
    logging.INFO, logging.WARNING, logging.ERROR, logging.ERROR]

class Agent:

    def __init__(self, config):
        parser = ConfigParser.RawConfigParser()
        parser.read(config)
        options = dict(parser.items('agent'))

        logging_config = options.get('logging', 'INFO')
        if '<logger>' in logging_config:
            import ZConfig
            ZConfig.configureLoggers(logging_config)
        else:
            logging.basicConfig(level=logging_config.upper())

        sentry_dsn = options.get('sentry_dsn')
        if sentry_dsn:
            import raven.handlers.logging
            logging.getLogger().addHandler(
                raven.handlers.logging.SentryHandler(sentry_dsn))

        aname = self.name = options.get('name', socket.getfqdn())
        self.base_interval = float(options.get('base_interval', 60.0))
        self.timeout = float(options.get('timeout', self.base_interval * .7))
        self.alert_timeout = float(options.get('alert_timeout',
                                               self.base_interval * .2))

        self.db = load_handler(parser, 'database')

        alerter = self.alerter = load_handler(parser, 'alerter')

        self._set_critical(self.db.get_faults(self.name))

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

    def _set_critical(self, faults):
        self.critical = dict(
            (f['name'], f['message'] if f.get('triggered') else -1)
            for f in faults
            if f['severity'] >= logging.CRITICAL
            )

    def perform(self, minute):
        # start checks. XXX maybe we want to limit the number of checks
        # running at once.
        checklets = [(check, gevent.spawn(check.perform))
                     for check in self.checks]

        deadline = time.time() + self.timeout
        faults = []
        critical = {}
        checked = set()
        squelches = None
        squelched = set()
        alerts = []
        for check, checklet in checklets:
            if not check.should_run(minute):
                continue
            checked.add(check.name)
            timeout = max(0, deadline - time.time())
            checklet.join(timeout)
            cresults = checklet.value
            if cresults is None:
                checklet.kill(block=False)
                cresults = dict(faults=[
                    monitor_error('timeout', severity=logging.CRITICAL)
                    ])
            for f in cresults.get('faults', ()):
                if f.get('name', ''):
                    name = check.name + '#' + f['name']
                else:
                    name = check.name
                f['name'] = name
                faults.append(f)
                if f['severity'] >= logging.CRITICAL:
                    if squelches is None:
                        squelches = self.db.get_squelches()
                    for squelch in squelches:
                        if re.search(squelch, name):
                            break
                    else:
                        message = f['message']
                        critical[name] = f
                        if (name in self.critical and
                            self.critical[name] == message):
                            # This is a previously triggered fault, so
                            # set triggered flag:
                            f['triggered'] = 'y'
                        else:
                            alerts.append(self.trigger(f))

        for name in self.critical:
            if name not in critical and name.split('#')[0] in checked:
                alerts.append(self.resolve(name))

        deadline = time.time() + self.alert_timeout
        alert_failed = 0
        for alert in alerts:
            timeout = max(deadline - time.time(), 0.0)
            alert.join(timeout)
            if not alert.value:
                exception = alert.exception
                logger.error("Alert failed: %s",
                             "timeout" if exception is None else
                             "%s: %s" % (exception.__class__.__name__,
                                         exception))
                alert_failed += 1

        if alert_failed:
            faults.append(dict(
                name = self.name + '#alerts',
                message = "Failed to send alert information (%s/%s)" % (
                    alert_failed, len(alerts)),
                severity = logging.CRITICAL,
                updated = time.time(),
                ))

        self.db.set_faults(self.name, faults)
        self._set_critical(critical.values())

    def trigger(self, fault):

        def trigger():
            self.alerter.trigger(fault['name'], fault['message'])
            fault['triggered'] = 'y' # DynamoDB does odd things with booleans
            return 1

        return gevent.spawn(trigger)

    def resolve(self, name):
        return gevent.spawn(lambda : [self.alerter.resolve(name)])

    def loop(self, count = -1):
        base_interval = self.base_interval
        last = time.time()
        while count:
            now = time.time()
            if now - last > base_interval:
                self.slow = True
            last = now
            tick = now / base_interval
            itick = int(tick)
            gevent.sleep(base_interval * (1 - (tick - itick)))
            self.perform(itick + 1)
            count -= 1

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

    def should_run(self, minute):
        interval = self.interval
        if self.failures:
            retry_interval = self.retry_interval
            if retry_interval == 1:
                return True
            minutes_failed = (self.failures - 1) * retry_interval
            minute_failed = (minute - minutes_failed - 1) / interval * interval
            last_fail = minute_failed + minutes_failed
            return minute - last_fail >= retry_interval

        return minute % interval == 0

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
            now = time.time()

            if status == 0 and stdout.startswith('{'):
                try:
                    result = json.loads(stdout)
                    for f in result['faults']:
                        if isinstance(f['severity'], basestring):
                            f['severity'] = severity_names[
                                f['severity'].lower()]
                        f['message']
                        f['updated'] = now
                except Exception, v:
                    logger.exception("Bad json response for %s", self.name)
                    result = dict(faults=[dict(
                        name='json-error',
                        message = "%s: %s" % (v.__class__.__name__, v),
                        severity = logging.CRITICAL,
                        updated = now,
                        )])
            else:
                faults = []
                result = dict(faults=faults)

                if stderr:
                    faults.append(monitor_error("stderr", stderr))

                stdout = stdout or stderr
                if not stdout:
                    faults.append(monitor_error("no-out"))
                    stdout = "(no output)"
                if len(stdout) > 200:
                    stdout = stdout[:200]+' ...'

                if status < 4:
                    if status:
                        faults.append(dict(severity=status_codes[status],
                                           message=stdout))
                else:
                    faults.append(monitor_error("status", stdout))
                    status = logging.CRITICAL

                for f in faults:
                    f['updated'] = now

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
                        f['message'] = "%s (%s of %s)" % (
                            f.get('message', ''), self.failures, self.chances)
            else:
                self.failures = 0

            return result
        except Exception, v:
            logger.exception("Checker failed %s", self.name)
            result = dict(faults=[dict(
                name='checker',
                message = "%s: %s" % (v.__class__.__name__, v),
                severity = logging.CRITICAL,
                updated = time.time(),
                )])

severity_names = dict(warning=logging.WARNING,
                      error=logging.ERROR,
                      critical=logging.CRITICAL)

def monitor_error(name, message='', prefix='', severity=logging.ERROR):
    return dict(
        name=(prefix + 'monitor-' + name),
        message=message,
        severity=severity,
        updated=time.time(),
        )

def load_handler(parser, name):
    config = dict(parser.items(name))
    mod, name = config['class'].split(':')
    mod = __import__(mod, {}, {}, [name])
    return getattr(mod, name)(config)

def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = argparse.ArgumentParser(description='Run monitoring agent.')
    parser.add_argument('configuration',
                        help='agent configuration file')
    parser.add_argument('-n', '--count', type=int,
                        help='number of tests to perform (default unlimited)')

    args = parser.parse_args(args)
    Agent(args.configuration).loop(args.count or -1)
