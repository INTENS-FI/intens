"""FMI support for Simsvc.

This should be installed as package "model".  Behaviour can be
modified by adding a module "custom".  The following customisations
are currently available:

process_results(recs, out)	Read simulation results from the structured
	array recs and add them in JSON serialisable form to the dict out
	(with variable names as keys).  Return out.  Defaults to
	.util.serialise_results.
"""

import os, tempfile, atexit
import dask, fmpy

tmp = fmu = None

try:
    from .custom import process_results
except ImportError:
    from .util import serialise_results as process_results

def cleanup():
    if tmp is not None:
        tmp.cleanup()
    tmp = fmu = None

def worker_callback():
    """Unpack the model into a temporary directory.

    The model file is given by the environment variable MODEL_FMU
    (full path), default model.fmu in the package directory.  This
    sets module variables tmp and fmu to point at a newly created
    tempfile.TemporaryDirectory and the extracted fmu, respectively.
    It also registers an atexit hook to remove tmp.
    """
    global tmp, fmu
    atexit.register(cleanup)
    if tmp is None:
        tmp = tempfile.TemporaryDirectory()
    if fmu is None:
        f = os.getenv("MODEL_FMU") or os.path.join(os.path.dirname(__file__),
                                                   "model.fmu")
        fmu = fmpy.extract(f, tmp.name)

@dask.delayed
def task(spec, cancel):
    t0 = t1 = Nome
    pars = {}
    unk = []
    warn = ""
    for k, v in spec.items():
        if k == "CITYOPT.simulation_start":
            t0 = v
        elif k == "CITYOPT.simulation_end":
            t1 = v
        elif k.startswith("p."):
            pars[k[2:]] = v
        else:
            unk.append(k)
    if unk:
        warn += "Unknown inputs: {}\n".format(", ".join(unk))
    recs = fmpy.simulate_fmu(fmu, start_time=t0, stop_time=t1,
                             start_values=pars)
    return process_results(recs, {'warnings': warn})
