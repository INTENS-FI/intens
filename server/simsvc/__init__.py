
def create_app():
    from .tasks import TaskFlask
    from .config import Config
    from . import jobs, vars

    app = TaskFlask(__name__)
    app.config.from_object(Config)
    app.register_blueprint(jobs.jobs_bp, url_prefix="/jobs")
    app.register_blueprint(vars.get_vars, url_prefix="/default",
                           url_defaults={"vtype": "default", "job": None})
    app.register_blueprint(
        vars.get_vars,
        url_prefix="/jobs/<int:job>/<any(inputs, results):vtype>")
    app.register_blueprint(vars.set_vars, url_prefix="/default")
    return app
