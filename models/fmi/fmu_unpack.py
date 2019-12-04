"""Manage extracted FMU contents.
"""

import os, tempfile, atexit, logging
import fmpy

tmp = fmu = None

logger = logging.getLogger(__name__)

def cleanup():
    global tmp, fmu
    if tmp is not None:
        logger.info("Cleaning up %s", tmp.name)
        tmp.cleanup()
    tmp = fmu = None

def unpack_model():
    """Unpack the model into a temporary directory.

    The model file is given by the environment variable MODEL_FMU
    (full path), default model.fmu in the package directory.  This
    sets module variables tmp and fmu to point at a newly created
    tempfile.TemporaryDirectory and the extracted fmu, respectively.
    It also registers an atexit hook to remove tmp.
    """
    global tmp, fmu
    if tmp is None:
        atexit.register(cleanup)
        tmp = tempfile.TemporaryDirectory()
        fmu = None
    if fmu is None:
        f = os.getenv("MODEL_FMU") or os.path.join(os.path.dirname(__file__),
                                                   "model.fmu")
        fmu = fmpy.extract(f, tmp.name)
        logger.info("Extracted FMU to %s", fmu)
