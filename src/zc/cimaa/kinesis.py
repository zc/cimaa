import json
import boto.kinesis

class Metrics:

    _sn = None

    def __init__(self, config):
        self._put = boto.kinesis.connect_to_region(config['region']).put_record
        self.stream = config['stream']
        self.partition_key = config.get('partition_key')
        self.explicit_hash_key = config.get('explicit_hash_key')

    def __call__(self, timestamp, name, value, units=''):
        data = json.dumps(
            dict(timestamp=timestamp, name=name, value=value, units=units))
        self._sn = self._put(
            self.stream,
            data,
            self.partition_key or name,
            self.explicit_hash_key,
            self._sn)['SequenceNumber']

