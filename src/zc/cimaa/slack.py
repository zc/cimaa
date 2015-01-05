#import gevent.monkey
#gevent.monkey.patch_all()
import slacker

class Alerter:

    def __init__(self, config):
        self.token = config['token']
        self.channel = config.get('channel') or 'general'
        self.target = config.get('target') or ''
        if not self.channel[0] == '#':
            self.channel = '#' + self.channel
        self.name = 'cimaa'
        self.slack = slacker.Slacker(self.token)

    def _broken(self, name):
        return '*' + ' '.join(name[2:].split('/', 2)) + '*'

    def trigger(self, name, message):
        self._post("_*Alert*_: %s: %s" % (self._broken(name) , message))

    def _post(self, message):
        if self.target:
            message = ' '.join((self.target, message))
        self.slack.chat.post_message(self.channel, message, username=self.name)

    def resolve(self, name):
        self._post("*Clear*: %s" % (self._broken(name)))
