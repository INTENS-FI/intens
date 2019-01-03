#!/usr/bin/python3

import logging, argparse

from socketIO_client import SocketIO

logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
logging.basicConfig()

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
    p.add_argument(
        'url', nargs='?', default="http://localhost:8080",
        help="Simsvc base URL (without trailing slash, default %(default)s)")
    args = p.parse_args()
    verify = False if args.trust else (args.cafile or True)
    with SocketIO(args.url, verify=verify) as sioc:
        sioc.on('launched', on_launched)
        sioc.on('terminated', on_terminated)
        sioc.wait()
