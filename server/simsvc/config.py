import os

class Config(object):
    SIMSVC_ADDR = os.environ.get("SIMSVC_ADDR", "localhost")
    WORK_DIR = os.environ.get("WORK_DIR", ".")
