"""Manage extracted FMU contents.
"""

import os, tempfile, atexit, logging
import dask.config, fmpy

tmp = fmu = None

logger = logging.getLogger(__name__)

def cleanup():
    global tmp, fmu
    if tmp is not None:
        logger.info("Cleaning up %s", tmp.name)
        tmp.cleanup()
    tmp = fmu = None

def expand_path(f):
    """Convert f to an absolute path.

    f can be an absolute path or relative to the package directory.
    The usual tilde constructions are expanded if possible.
    """
    return os.path.join(os.path.dirname(__file__),
                        os.path.expanduser(f))

def unpack_model():
    """Unpack the model into a temporary directory.

    The model file is given by the environment variable MODEL_FMU or
    Dask config item simsvc.model.fmu.  Default is "model.fmu".  The
    file name is processed with expand_path.

    This sets module variables tmp and fmu to point at a newly created
    tempfile.TemporaryDirectory and the extracted fmu, respectively.
    It also registers an atexit hook to remove tmp.
    """
    global tmp, fmu
    if tmp is None:
        atexit.register(cleanup)
        tmp = tempfile.TemporaryDirectory()
        fmu = None
    if fmu is None:
        f = os.getenv("MODEL_FMU") or dask.config.get("simsvc.model.fmu",
                                                      "model.fmu")
        fmu = fmpy.extract(os.path.join(os.path.dirname(__file__),
                                        os.path.expanduser(f)),
                           tmp.name)
        logger.info("Extracted FMU to %s", fmu)
