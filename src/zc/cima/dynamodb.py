# Dynamodb implementation

from boto import dynamodb2
import boto.dynamodb2.fields
import boto.dynamodb2.table
import boto.dynamodb2.types
import time

schemas = dict(
    agents = dict(schema=[dynamodb2.fields.HashKey('name')]),
    squelches = dict(schema=[dynamodb2.fields.HashKey('regex')]),
    faults = dict(schema=[dynamodb2.fields.HashKey('agent'),
                          dynamodb2.fields.RangeKey('name')]),
    )

class DB:

    def __init__(self, config, tables=tuple(schemas)):
        self.last_faults = {}
        conn, prefix = connect(config)
        for name in schemas:
            setattr(self, name, table(conn, prefix, name))

    def get_faults(self, agent):
        faults = [dict(item.items())
                  for item in self.faults.query_2(agent__eq=agent)]
        self.last_faults[agent] = set(fault['name'] for fault in faults)
        return faults

    def set_faults(self, agent, faults):
        old_faults = self.last_faults.get(agent)
        if old_faults is None:
            self.get_faults(agent)
            old_faults = self.last_faults.get(agent)

        if faults or old_faults:
            with self.faults.batch_write() as batch:
                for fault in faults:
                    data = fault.copy()
                    data['agent'] = agent
                    batch.put_item(data, overwrite=True)
                    old_faults.discard(data['name'])
                for name in old_faults:
                    batch.delete_item(agent=agent, name=name)

        if not faults:
            self.agents.put_item(dict(name=agent, updated=time.time()),
                                 overwrite=True)

        self.last_faults[agent] = set(fault['name'] for fault in faults)

    def get_squelches(self):
        return [item['regex'] for item in self.squelches.scan()]

    def squelch(self, regex, reason, user):
        self.squelches.put_item(dict(regex=regex,
                                     reason=reason,
                                     user=user,
                                     time=time.time(),
                                     ))

    def unsquelch(self, regex):
        self.squelches.delete_item(regex=regex)

    def dump(self, name=None):
        if name:
            return [dict(item.items()) for item in getattr(self, name).scan()]
        return dict(
            agents = [dict(item.items()) for item in self.agents.scan()],
            faults = [dict(item.items()) for item in self.faults.scan()],
            squelches = [dict(item.items()) for item in self.squelches.scan()],
            )

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
    return dict(parser.items('database'))

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

    tables = [create(conn, prefix, name) for name in schemas]
    while tables:
        if tables[-1].describe()['Table']['TableStatus'] == 'ACTIVE':
            tables.pop()
        time.sleep(1)

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
    parser.add_argument('-r', '--remove', action='store_true',
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

