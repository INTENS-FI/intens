import os

class Config(object):
    SIMSVC_ADDR = os.environ.get("SIMSVC_ADDR", "localhost:8080")
    """Listening address of the HTTP server.
    See util.addrstr for the format.
    """

    WORK_DIR = os.environ.get("WORK_DIR", ".")
    """The parent of task work directories"""
