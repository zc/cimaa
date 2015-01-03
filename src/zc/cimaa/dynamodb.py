# Dynamodb implementation

from boto import dynamodb2
import boto.dynamodb2.exceptions
import boto.dynamodb2.fields
import boto.dynamodb2.table
import boto.dynamodb2.types
import sys
import time

schemas = dict(
    squelches=dict(schema=[dynamodb2.fields.HashKey('regex')]),
    faults=dict(schema=[dynamodb2.fields.HashKey('agent'),
                        dynamodb2.fields.RangeKey('name')],
                indexes=[
                    dynamodb2.fields.IncludeIndex(
                        'updated',
                        parts=[
                            dynamodb2.fields.HashKey('agent'),
                            dynamodb2.fields.RangeKey(
                                'updated',
                                data_type=boto.dynamodb2.types.NUMBER),
                            ],
                        includes=['name', 'updated'],
                        )
                    ],
                ),
    )

class DB:

    def __init__(self, config, tables=tuple(schemas)):
        self.last_faults = {}
        conn, prefix = connect(config)
        for name in schemas:
            setattr(self, name, table(conn, prefix, name))

    def old_agents(self, age):
        max_updated = time.time() - age
        return [dict(name=i['name'], updated=i['updated'])
                for i in self.faults.query_2(
                    index='updated', agent__eq='_', updated__lt=max_updated)]

    def get_faults(self, agent):
        faults = [dict(item.items())
                  for item in self.faults.query_2(agent__eq=agent)]
        # dynamodb doesn't populate keys with empty strings
        for f in faults:
            if 'message' not in f:
                f[u'message'] = u''
        self.last_faults[agent] = set(fault['name'] for fault in faults)
        return faults

    def set_faults(self, agent, faults):
        old_faults = self.last_faults.get(agent)
        if old_faults is None:
            self.get_faults(agent)
            old_faults = self.last_faults.get(agent)

        with self.faults.batch_write() as batch:
            # Heartbeat
            batch.put_item(dict(agent='_', name=agent, updated=time.time()))

            for fault in faults:
                data = fault.copy()
                data['agent'] = agent
                batch.put_item(data, overwrite=True)
                old_faults.discard(data['name'])
            for name in old_faults:
                batch.delete_item(agent=agent, name=name)

        self.last_faults[agent] = set(fault['name'] for fault in faults)

    def get_squelch(self, regex):
        try:
            item = self.squelches.lookup(regex)
        except boto.dynamodb2.exceptions.ItemNotFound:
            return None
        return dict(item.items())

    def get_squelches(self):
        return [item['regex']
                for item in self.squelches.scan(attributes=['regex'])]

    def squelch(self, regex, reason, user):
        self.squelches.put_item(dict(regex=regex,
                                     reason=reason,
                                     user=user,
                                     time=time.time(),
                                     ))

    def unsquelch(self, regex):
        self.squelches.delete_item(regex=regex)

    def dump(self, name=None):
        return dict(
            faults = sorted(
                (dict(item.items()) for item in self.faults.scan()),
                key=lambda item: (item['agent'], item['name'])),
            squelches = sorted(
                (dict(item.items()) for item in self.squelches.scan()),
                key=lambda item: ['regex']),
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
    import zc.cimaa.parser
    return zc.cimaa.parser.parse_file(filename).get('database', {})

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
