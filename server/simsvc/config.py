"""Simsvc configuration support.
This is a bit of a mess because there is both Flask and Dask style config.
Flask config is generally used for web server stuff and Dask config for
distributed computation.
"""

import os
import yaml, dask.config

class Config(object):
    SIMSVC_ADDR = os.environ.get("SIMSVC_ADDR", "localhost:8080")
    """Listening address of the HTTP server.
    See .util.addrstr for the format.
    """

    SIMSVC_ROOT = os.environ.get("SIMSVC_ROOT", "/")
    """Root path of the app.
    """

    WORK_DIR = os.environ.get("WORK_DIR", None)
    """The parent of job work directories or false to disable
    job work directories
    """

    JOB_DB = os.environ.get("JOB_DB", None)
    """The job database URL, parsed by zodburi.
    The default is file storage simsvc.fs in the current directory.
    """

    HTPASSWD_FILE = os.environ.get("HTPASSWD_FILE", None)
    """An optional htpasswd file to enable authentication.
    """

config_file = os.path.join(os.path.dirname(__file__), "simsvc.yaml")

def read_config_file():
    with open(config_file) as f:
        return yaml.load(f)

dask.config.update_defaults(read_config_file())
dask.config.ensure_file(source=config_file)
