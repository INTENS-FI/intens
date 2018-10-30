#!/usr/bin/python3

"""A script for running the simsvc server.

This always uses eventlet.wsgi, bypassing SocketIO.run because it does
not support AF_UNIX.
"""

import atexit
from socket import AddressFamily as AF

from simsvc import create_app
from simsvc.util import addrstr, tryrm

if __name__ == '__main__':
    import eventlet
    from eventlet import wsgi
    app = create_app(async_mode='eventlet')

    addr, af = addrstr(app.config['SIMSVC_ADDR'])
    if af == getattr(AF, 'AF_UNIX', None):
        tryrm(addr)
        atexit.register(tryrm, addr)
    wsgi.server(eventlet.listen(addr, af), app)
