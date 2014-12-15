"""Parse ConfigParser data into dicts
"""
import ConfigParser

def parse_text(text):
    parser = ConfigParser.RawConfigParser()
    import StringIO
    parser.readfp(StringIO.StringIO(text))
    return parser_dict(parser)

def parse_file(name):
    parser = ConfigParser.RawConfigParser()
    parser.read(name)
    return parser_dict(parser)

def parser_dict(parser):
    return dict((section, dict(parser.items(section)))
                for section in parser.sections())
