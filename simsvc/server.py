#!/usr/bin/python3

import logging, os, atexit
from socket import AddressFamily as AF

from util import addrstr, tryrm
from tasks import TaskFlask

def create_app():
    import jobs, vars

    app = TaskFlask(__name__)
    app.register_blueprint(jobs.jobs_bp, url_prefix="/jobs")
    app.register_blueprint(vars.get_vars, url_prefix="/default",
                           url_defaults={"vtype": "default", "job": None})
    app.register_blueprint(
        vars.get_vars,
        url_prefix="/jobs/<int:job>/<any(inputs, results):vtype>")
    app.register_blueprint(vars.set_vars, url_prefix="/default")
    return app

if __name__ == '__main__':
    from eventlet import wsgi, listen

    app = create_app()

    # As a side effect this ensures that app.db and app.client are created.
    # If either one is going to fail, we want to know now.
    app.logger.info("Connected to database %s", app.db.storage.getName())
    cores = app.client.ncores()
    app.logger.info("%d workers with %d cores",
                    len(cores), sum(cores.values()))

    addr, af = addrstr(os.environ.get("SIMSVC_ADDR", "localhost"))
    if af == AF.AF_UNIX:
        tryrm(addr)
        atexit.register(tryrm, addr)
    wsgi.server(listen(addr, af), app)
