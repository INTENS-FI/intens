"""Distributed simulation service.
"""

def create_app(**kws):
    """Create and return the simulation server Flask app.
    
    kws is passed to the SocketIO constructor.
    
    Also start up coroutines to periodically sync tasks and pack the ZODB
    database unless socketio.async_mode is 'threading', in which case only sync
    and pack once to avoid concurrency issues.  async_mode can be forced by
    specifying it in kws, otherwise the Sockiet.IO library auto-detects and
    prefers Eventlet.  We assume that greenthreads are safe against concurrency
    issues, in particular the standard library has not been monkey-patched.
    """
    from urllib.parse import urljoin
    from flask_socketio import SocketIO

    from .tasks import TaskFlask
    from .config import Config
    from . import sockio, jobs, vars

    app = TaskFlask(__name__)
    app.config.from_object(Config)

    p = app.config['SIMSVC_ROOT']

    socketio = sockio.bind_socketio(app, path=urljoin(p, "socket.io"), **kws)

    app.register_blueprint(jobs.jobs_bp, url_prefix=urljoin(p, "jobs"))
    app.register_blueprint(vars.get_vars, url_prefix=urljoin(p, "default"),
                           url_defaults={"vtype": "default", "job": None})
    app.register_blueprint(
        vars.get_vars,
        url_prefix=urljoin(p, "jobs/<int:job>/<any(inputs, results):vtype>"))
    app.register_blueprint(vars.set_vars, url_prefix=urljoin(p, "default"))

    # As a side effect this ensures that app.db and app.client are created.
    # If either one is going to fail, we want to know now.
    app.logger.info("Connected to database %s", app.db.storage.getName())
    cores = app.client.ncores()
    app.logger.info("%d workers with %d cores",
                    len(cores), sum(cores.values()))

    if socketio.async_mode == 'threading':
        app.logger.info("Periodic sync & pack disabled; only doing once.")
        app.sync_tasks()
        app.db.pack(days=7)
    else:
        def task_syncer():
            while True:
                app.sync_tasks()
                socketio.sleep(30)
        def zodb_packer():
            while True:
                app.logger.info("Packing the database")
                app.db.pack(days=7)
                socketio.sleep(86400) # 24 h
        socketio.start_background_task(task_syncer)
        socketio.start_background_task(zodb_packer)

    return app
