import argparse
import getpass
import os
import zc.cimaa.parser


def getuser():
    user = getpass.getuser()
    if user == "root" and "SUDO_USER" in os.environ:
        user = os.environ["SUDO_USER"]
    return user
        

def squelch(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(description='Add a squelch.')
    parser.add_argument('configuration',
                        help='agent configuration file')
    parser.add_argument('regex',
                        help='regular expression to be squelched')
    parser.add_argument('reason', nargs='?', default=None,
                        help='The reason for this squelch')
    parser.add_argument('-p', '--permanent', action='store_true',
                        help='Make the squelch permanent')
    args = parser.parse_args(args)
    db = zc.cimaa.parser.load_handler(
        zc.cimaa.parser.parse_file(args.configuration)['database'])
    if args.reason is None:
        raise ValueError("A reason must be supplied when adding squelches")
    db.squelch(args.regex, args.reason, getuser(), args.permanent)


def unsquelch(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(description='Remove a squelch.')
    parser.add_argument('configuration',
                        help='agent configuration file')
    parser.add_argument('regex',
                        help='regular expression to be squelched')
    args = parser.parse_args(args)
    db = zc.cimaa.parser.load_handler(
        zc.cimaa.parser.parse_file(args.configuration)['database'])
    db.unsquelch(args.regex)
