# Dynamodb implementation

from boto import dynamodb2
import boto.dynamodb2.exceptions
import boto.dynamodb2.fields
import boto.dynamodb2.table
import boto.dynamodb2.types
import sys
import time
import zc.cimaa.parser

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
        return [dict(name=i['name'], updated=int(i['updated']))
                for i in self.faults.query_2(
                    index='updated', agent__eq='_', updated__lt=max_updated)]

    def get_faults(self, agent):
        faults = [_fault_data(item)
                  for item in self.faults.query_2(agent__eq=agent)]
        self.last_faults[agent] = set(fault['name'] for fault in faults)
        return faults

    def set_faults(self, agent, faults):
        old_faults = self.last_faults.get(agent)
        if old_faults is None:
            self.get_faults(agent)
            old_faults = self.last_faults.get(agent)

        with self.faults.batch_write() as batch:
            # Heartbeat
            batch.put_item(dict(agent='_', name=agent, updated=int(time.time())))

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
        return _squelch_data(item)

    def get_squelches(self):
        return sorted(item['regex']
                      for item in self.squelches.scan(attributes=['regex'])
                      )

    def get_squelch_details(self):
        return sorted((_squelch_data(item) for item in self.squelches.scan()),
                      key=_squelch_regex)

    def squelch(self, regex, reason, user, permanent=False):
        self.squelches.put_item(dict(regex=regex,
                                     reason=reason,
                                     user=user,
                                     permanent = 'p' if permanent else '',
                                     time=int(time.time()),
                                     ))

    def unsquelch(self, regex):
        self.squelches.delete_item(regex=regex)

    def dump(self, name=None):
        return dict(
            faults = sorted(
                (_fault_data(dict(item.items()))
                 for item in self.faults.scan()),
                key=lambda item: (item['agent'], item['name'])),
            squelches = sorted(
                (_squelch_data(dict(item.items()))
                 for item in self.squelches.scan()),
                key=lambda item: ['regex']),
            )

def _fault_data(item):
    data = dict(item.items())
    # dynamodb doesn't populate keys with empty strings
    if u'message' not in data:
        data[u'message'] = u''
    if u'updated' in data:
        try:
            data[u'updated'] = int(data[u'updated'])
        except ValueError:
            # Existing data may be a float, so add a step to the conversion:
            data[u'updated'] = int(float(data[u'updated']))
    if u'severity' in data:
        # Ints, not Decimals:
        data[u'severity'] = int(data[u'severity'])
    return data

def _squelch_data(item):
    data = dict(item.items())
    data[u'permanent'] = bool(data.get(u'permanent'))
    try:
        data[u'time'] = int(data[u'time'])
    except ValueError:
        # Existing data may be a float, so add a step to the conversion:
        data[u'time'] = int(float(data[u'time']))
    return data

def _squelch_regex(data):
    return data['regex']

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
    return zc.cimaa.parser.parse_file(filename)['database']

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
