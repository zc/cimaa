"""Parse ConfigParser data into dicts
"""
from ConfigParser import Error
import ConfigParser

def parse_text(text):
    parser = ConfigParser.RawConfigParser()
    parser.optionxform = str
    import StringIO
    parser.readfp(StringIO.StringIO(text))
    return parser_dict(parser)

def parse_file(name):
    parser = ConfigParser.RawConfigParser()
    parser.optionxform = str
    parser.read(name)
    return parser_dict(parser)

def parser_dict(parser):
    return dict((section, dict(parser.items(section)))
                for section in parser.sections())

def load_handler(config):
    mod, name = config['class'].split(':')
    mod = __import__(mod, {}, {}, [name])
    return getattr(mod, name)(config)
