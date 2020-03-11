"""Simsvc configuration support.
This is a bit of a mess because there is both Flask and Dask style config.
Flask config is generally used for web server stuff and Dask config for
distributed computation.
"""

import os
import yaml, dask.config

defaults_file = os.path.join(os.path.dirname(__file__), "simsvc.yaml")

def read_defaults_file():
    with open(defaults_file) as f:
        return yaml.safe_load(f)

dask.config.update_defaults(read_defaults_file())
dask.config.ensure_file(source=defaults_file)

def _env_conf(env, conf):
    return os.environ.get(env, None) or dask.config.get("simsvc." + conf)

class Config(object):
    """Flask config.

    This is now backed by dask.config, although for historical reasons
    there are special enviroment variables that take precedence.  See
    simsvc.server in simsvc.yaml for documentation.
    """

    SIMSVC_ADDR = _env_conf("SIMSVC_ADDR", "server.address")
    SIMSVC_ROOT = _env_conf("SIMSVC_ROOT", "server.root")
    WORK_DIR = _env_conf("WORK_DIR", "server.work_dir")
    JOB_DB = _env_conf("JOB_DB", "server.job_db")
    HTPASSWD_FILE = _env_conf("HTPASSWD_FILE", "server.htpasswd_file")
