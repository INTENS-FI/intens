import os

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
