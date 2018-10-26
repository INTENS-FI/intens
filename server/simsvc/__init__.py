"""Distributed simulation service.
"""

def create_app():
    """Create and return the simulation server Flask app.
    """
    from .tasks import TaskFlask
    from .config import Config
    from . import sockio, jobs, vars

    app = TaskFlask(__name__)
    app.config.from_object(Config)

    sockio.socketio.init_app(app)
    app.monitor = sockio.Monitor(app)

    app.register_blueprint(jobs.jobs_bp, url_prefix="/jobs")
    app.register_blueprint(vars.get_vars, url_prefix="/default",
                           url_defaults={"vtype": "default", "job": None})
    app.register_blueprint(
        vars.get_vars,
        url_prefix="/jobs/<int:job>/<any(inputs, results):vtype>")
    app.register_blueprint(vars.set_vars, url_prefix="/default")
    return app
