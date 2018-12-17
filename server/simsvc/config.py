import os

class Config(object):
    SIMSVC_ADDR = os.environ.get("SIMSVC_ADDR", "localhost:8080")
    """Listening address of the HTTP server.
    See .util.addrstr for the format.
    """

    WORK_DIR = os.environ.get("WORK_DIR", None)
    """The parent of job work directories or false to disable
    job work directories
    """
