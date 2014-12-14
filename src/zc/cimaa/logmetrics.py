import json
import logging

class LogMetrics:

    def __init__(self, config):
        self.logger = logging.getLogger(config.get('name', 'metrics'))

    def __call__(self, timestamp, name, value, units=''):
        self.logger.info(json.dumps(dict(
            timestamp=timestamp, name=name, value=value, units=units)))
