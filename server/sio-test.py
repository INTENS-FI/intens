#!/usr/bin/python3

import logging, argparse

import socketio

logging.basicConfig()
logger = logging.getLogger(__name__)

def on_launched(jid):
    print("Launched", jid)

def on_terminated(arg):
    print("Terminated", arg)

if __name__ == '__main__':
    p = argparse.ArgumentParser(description="Simsvc Socket.IO test client")
    p.add_argument('-c', '--cafile', default=None,
                   help="Root CA bundle for SSL verification")
    p.add_argument('-t', '--trust', action='store_true',
                   help="Disable SSL certificate verification")
    p.add_argument('-v', '--verbose', action='count',
                   help="Enable Engine.IO logging.  -vv for debug level.")
    p.add_argument(
        'url', nargs='?', default="http://localhost:8080",
        help="Simsvc base URL (without trailing slash, default %(default)s)")
    args = p.parse_args()
    verify = False if args.trust else (args.cafile or True)
    if args.verbose:
        eio_log = logger
        if args.verbose > 1:
            logger.setLevel(logging.DEBUG)
    else:
        eio_log = False
    sioc = socketio.Client(ssl_verify=verify, engineio_logger=eio_log)
    sioc.on('launched', on_launched)
    sioc.on('terminated', on_terminated)
    sioc.connect(args.url)
    sioc.wait()
