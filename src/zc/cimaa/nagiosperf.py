r"""Parser for nagios performance data

    >>> import pprint
    >>> def ppp(text):
    ...     pprint.pprint(parse_output(text))

    >>> ppp("DISK OK - free space: / 3326 MB (56%);")
    ('DISK OK - free space: / 3326 MB (56%);\n', [])

    >>> ppp(
    ... "DISK OK - free space: / 3326 MB (56%); | /=2643MB;5948;5958;0;5968")
    ('DISK OK - free space: / 3326 MB (56%); \n',
     [{'name': '/', 'units': 'MB', 'value': 2643.0}])

    >>> ppp(
    ... '''DISK OK - free space: / 3326 MB (56%); | /=2643MB;5948;5958;0;5968
    ... / 15272 MB (77%);
    ... /boot 68 MB (69%);
    ... /home 69357 MB (27%);
    ... /var/log 819 MB (84%); | /boot=68MB;88;93;0;98
    ... /home=69357MB;253404;253409;0;253414
    ... /var/log=818MB;970;975;0;980''')
    ('DISK OK - free space: / 3326 MB (56%);
       \n/ 15272 MB (77%);\n/boot 68 MB (69%);\n/home 69357 MB
       (27%);\n/var/log 819 MB (84%); ',
     [{'name': '/', 'units': 'MB', 'value': 2643.0},
      {'name': '/boot', 'units': 'MB', 'value': 68.0},
      {'name': '/home', 'units': 'MB', 'value': 69357.0},
      {'name': '/var/log', 'units': 'MB', 'value': 818.0}])

    >>> ppp("PING ok - Packet loss = 0%, RTA = 0.80 ms "
    ...              "| percent_packet_loss=0, rta=0.80")
    ('PING ok - Packet loss = 0%, RTA = 0.80 ms \n',
     [{'name': 'percent_packet_loss', 'units': ',', 'value': 0.0},
      {'name': 'rta', 'units': '', 'value': 0.8}])

    >>> ppp("| 'ha ha ha'=3has")
    ('\n', [{'name': "'ha ha ha'", 'units': 'has', 'value': 3.0}])

See: https://nagios-plugins.org/doc/guidelines.html#AEN200
"""

import re

perf_parse = re.compile(
    r"([^=' \t]+|'[^=']+')"         # label
    r"="                           # =
    r"(\d+(\.\d*)?|\.\d+)"         # value
    r"([^; \t]*)"                      # Units
    r"(;(\d+(\.\d*)?|\.\d+)){0,4}" # warn, crit, min, max
    ).findall

def parse_output(text):
    texts = text.split('\n', 1)
    first = texts[0]
    rest = texts[1] if len(texts) > 1 else ''
    first = first.split('|', 1)
    rest = rest.split('|', 1)
    perf = ((first[1] + ' ' if len(first) > 1 else '') +
            (rest[1].replace('\n', '') if len(rest) > 1 else ''))
    return (
        first[0] + '\n' + rest[0],
        [dict(name=m[0], value=float(m[1]), units=m[3])
         for m in perf_parse(perf)],
        )

