# Dynamodb implementation

from boto import dynamodb2
import boto.dynamodb2.fields
import boto.dynamodb2.table
import boto.dynamodb2.types
import time

schemas = dict(
    agents = dict(
        schema=[dynamodb2.fields.HashKey('name')],
        indexes=[dynamodb2.fields.AllIndex(
            "updated",
            parts=[dynamodb2.fields.RangeKey(
                'updated', data_type=boto.dynamodb2.types.NUMBER)],
            )],
        ),
    alerts = dict(
        schema=[dynamodb2.fields.HashKey('name')],
        indexes=[dynamodb2.fields.AllIndex(
            "start",
            parts=[dynamodb2.fields.RangeKey(
                'start', data_type=boto.dynamodb2.types.NUMBER)],
            )],
        ),
    squelches = dict(schema=[dynamodb2.fields.HashKey('regex')]),
    faults = dict(schema=[dynamodb2.fields.HashKey('agent'),
                          dynamodb2.fields.RangeKey('name')]),
    )

class DB:

    def __init__(self, config, tables=tuple(schemas)):
        conn, prefix = connect(config)
        for name in tables:
            setattr(self, name, table(conn, prefix, name))

    def heartbeat(self, agent, status):
        self.agents.put_item(dict(
            name=agent,
            updated=time.time(),
            status=status,
            ), overwrite=True)

    def old_agents(self, min_age):
        max_time = time.time() - min_age
        for data in self.agents.query_2(
            index='updated',
            updated__lt=max_time
            ):
            yield dict(data.items())

    def alert_start(self, name):
        self.alerts.put_item(dict(name=name, time=time.time()), overwrite=True)

    def alert_finished(self, name):
        self.alerts.get_item(name=name).delete()

    def old_alerts(self, min_age):
        max_time = time.time() - min_age
        for data in self.alerts.query_2(
            index='start',
            start__lt=max_time
            ):
            yield dict(data.items())

    def get_faults(self, agent):
        retrun [dict(item.items())
                for item in self.faults.query_2(agent__eq=agent)]

    def set_faults(self, agent, faults):
        for fault in faults:
            data = fault.copy()
            data['agent'] = agent
            self.faults.put_item(data)

    def get_squelches(self):
        return [item['regex'] for item in self.squelches.scan()]

    def squelch(self, regex, reason, user):
        self.squelches.put_item(dict(regex=args.regex,
                                     reason=args.reason,
                                     user=getpass.getuser(),
                                     time=time.time(),
                                     ))

    def unsquelch(self, regex):
        squelches.get_item(regex__eq=regex).delete()

def connect(config):
    if 'aws_access_key_id' in config:
        conn = dynamodb2.connect_to_region(
            config['region'],
            aws_access_key_id = config['aws_access_key_id'],
            aws_secret_access_key = config['aws_secret_access_key'],
            )
    else:
        conn = dynamodb2.connect_to_region(config['region'])

    prefix = config['prefix']
    if not prefix[-1] == '.':
        prefix += '.'
    return conn, prefix

def config_parse(filename):
    import ConfigParser
    parser = ConfigParser.RawConfigParser()
    parser.read(filename)
    return = dict(parser.items('database'))

def setup(args=None):
    if args is None:
        args = sys.argv[1:]

    import argparse
    parser = argparse.ArgumentParser(
        description='Setup DynamoDB monitoring tables.')
    parser.add_argument('configuration',
                        help='agent configuration file')
    args = parser.parse_args(args)
    config = config_parse(args.configuration)
    conn, prefix = connect(config)

    for name in schamas:
        create(conn, prefix, name)

def create(conn, prefix, name):
    return dynamodb2.table.Table.create(
        prefix + name, connection=conn, **schemas[name])

def table(conn, prefix, name):
    return dynamodb2.table.Table(
        prefix + name, connection=conn, **schemas[name])

def squelch(args=None):
    if args is None:
        args = sys.argv[1:]

    import argparse, getpass
    parser = argparse.ArgumentParser(description='Add a squelch.')
    parser.add_argument('configuration',
                        help='agent configuration file')
    parser.add_argument('regex',
                        help='regular expression to be squelched')
    parser.add_argument('reason', nargs='?', default=None,
                        help='The reason for this squelch')
    parser.add_argument('-r', '--remove', action='store_true'
                        help='remove, rather than add the squelch')
    args = parser.parse_args(args)
    config = config_parse(args.configuration)
    db = DB(config_parse(args.configuration), tables=('squelches'))
    conn, prefix = connect(config)

    squelches = table(conn, prefix, 'squelches')
    if args.remove:
        db.unsquelch(args.regex)
    else:
        if args.reason is None:
            raise ValueError("A reason must be supplied when adding squelches")
        db.squelch(args.regex, args.reason, getpass.getuser())

