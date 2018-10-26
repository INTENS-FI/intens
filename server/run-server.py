#!/usr/bin/python3

import atexit
from socket import AddressFamily as AF

from simsvc import create_app
from simsvc.util import addrstr, tryrm

if __name__ == '__main__':
    from simsvc.sockio import socketio

    app = create_app()

    # As a side effect this ensures that app.db and app.client are created.
    # If either one is going to fail, we want to know now.
    app.logger.info("Connected to database %s", app.db.storage.getName())
    cores = app.client.ncores()
    app.logger.info("%d workers with %d cores",
                    len(cores), sum(cores.values()))

    def task_syncer():
        while True:
            app.sync_tasks()
            socketio.sleep(30)
    socketio.start_background_task(task_syncer)

    def zodb_packer():
        while True:
            app.logger.info("Packing the database")
            app.db.pack(days=7)
            socketio.sleep(86400) # 24 h
    socketio.start_background_task(zodb_packer)

    addr, af = addrstr(app.config['SIMSVC_ADDR'])
    if af == AF.AF_UNIX:
        raise ValueError("Sorry, Socket.IO does not do AF_UNIX")
        tryrm(addr)
        atexit.register(tryrm, addr)
    socketio.run(app, *addr)
