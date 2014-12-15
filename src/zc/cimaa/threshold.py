"""Threshold handling

Required thresholds fault if no metric:

    >>> r = Threshold(
    ...     'foo critical > 200 warning > 50 error > 99 clear < 80').check
    >>> r([dict(name='foo', value=42)])
    >>> pp(r([]))
    {'message': 'Missing metric', 'severity': 40}

    >>> o = Threshold('foo ? warning >= 50 error >= 99').check
    >>> o([dict(name='foo', value=42)])
    >>> o([])

Error levels:

    >>> pp(r([dict(name='foo', value=51)]))
    {'message': '51 > 50', 'severity': 30}
    >>> pp(o([dict(name='foo', value=50)]))
    {'message': '50 >= 50', 'severity': 30}

    >>> pp(r([dict(name='foo', value=100)]))
    {'message': '100 > 99', 'severity': 40}
    >>> pp(o([dict(name='foo', value=99)]))
    {'message': '99 >= 99', 'severity': 40}

    >>> pp(r([dict(name='foo', value=300)]))
    {'message': '300 > 200', 'severity': 50}

Errors stick even when we drop below error level until they clear

    >>> pp(r([dict(name='foo', value=100)]))
    {'message': '100 > 99', 'severity': 40}
    >>> pp(r([dict(name='foo', value=90)]))
    {'message': '90 not clear < 80', 'severity': 40}
    >>> pp(r([dict(name='foo', value=80)]))
    {'message': '80 not clear < 80', 'severity': 40}
    >>> pp(r([dict(name='foo', value=60)]))
    {'message': '60 > 50', 'severity': 30}
    >>> r([dict(name='foo', value=40)])

"""
import logging

class Thresholds:

    def __init__(self, definition):
        self.thresholds = [
            Threshold(line)
            for line in definition.strip().split('\n')
            if line]

    def __call__(self, results):
        metrics = results.get('metrics', ())
        for threshold in self.thresholds:
            f = threshold.check(metrics)
            if f is not None:
                f['name'] = threshold.name
                results['faults'].append(f)

class Threshold:

    optional = bad = False
    warning = error = critical = clear = None

    def __init__(self, definition):
        tokens = definition.strip().split()
        self.name = tokens.pop(0)
        if tokens[0] == '?':
            self.optional = True
            tokens.pop(0)

        try:
            while tokens:
                level = tokens.pop(0).lower()
                if level not in levels:
                    raise ValueError("Bad level %r" % level)
                opname = tokens.pop(0)
                threshold = tokens.pop(0)
                op = ops[opname](float(threshold))
                if level == 'clear':
                    opname = 'not clear ' + opname
                setattr(self, level, (op, '%%s %s %s' % (opname, threshold)))

        except Exception, v:
            raise ValueError("Invalid threshold definition, %r (%s)",
                             definition, v)

    def check(self, metrics):
        v = [m for m in metrics if m['name'] == self.name]
        if not v:
            if not self.optional:
                return dict(severity=logging.ERROR, message='Missing metric')
            return
        [v] = v
        v = v['value']

        if self.critical and self.critical[0](v):
            self.bad = True
            return dict(severity = logging.CRITICAL,
                        message  = self.critical[1] % v,
                        )
        if self.error and self.error[0](v):
            self.bad = True
            return dict(severity = logging.ERROR,
                        message  = self.error[1] % v,
                        )

        if self.bad and self.clear:
            if self.clear[0](v):
                bad = None
            else:
                return dict(severity = logging.ERROR,
                            message  = self.clear[1] % v,
                            )

        if self.warning and self.warning[0](v):
            return dict(severity = logging.WARNING,
                        message  = self.warning[1] % v,
                        )

        return None

levels = ('warning', 'error', 'critical', 'clear')

ops = {
    '>':  (lambda t: (lambda v: v >  t)),
    '>=': (lambda t: (lambda v: v >= t)),
    '==': (lambda t: (lambda v: v == t)), # nfc :)
    '<':  (lambda t: (lambda v: v <  t)),
    '<=': (lambda t: (lambda v: v <= t)),
    }
