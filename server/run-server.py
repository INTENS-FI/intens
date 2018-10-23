#!/usr/bin/python3

import atexit
from socket import AddressFamily as AF

from simsvc import create_app
from util import addrstr, tryrm

if __name__ == '__main__':
    from eventlet import wsgi, listen

    app = create_app()

    # As a side effect this ensures that app.db and app.client are created.
    # If either one is going to fail, we want to know now.
    app.logger.info("Connected to database %s", app.db.storage.getName())
    cores = app.client.ncores()
    app.logger.info("%d workers with %d cores",
                    len(cores), sum(cores.values()))

    addr, af = addrstr(app.config['SIMSVC_ADDR'])
    if af == AF.AF_UNIX:
        tryrm(addr)
        atexit.register(tryrm, addr)
    wsgi.server(listen(addr, af), app)
