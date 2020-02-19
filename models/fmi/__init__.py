"""FMI support for Simsvc.

This should be installed as package "model".  Behaviour can be
modified by adding a module "custom".  The following customisations
are currently available:

process_results(recs, out)	Read simulation results from the structured
	array recs and add them in JSON serialisable form to the dict out
	(with variable names as keys).  Return out.  Defaults to
	.util.serialise_results.

This module can also be configured using dask.config keys under simsvc.model:
fmu	FMU to load.  Env. var. MODEL_FMU overrides.  Default is "model.fmu".
	Processed with .fmu_unpack.expand_path, which see.
timeout	Simulation timeout in seconds or None (default).
	Passed to the FMI library.
"""

import os, logging
import dask, fmpy

logger = logging.getLogger(__name__)

fmu_file = os.getenv("MODEL_FMU") or dask.config.get("simsvc.model.fmu",
                                                     "model.fmu")
timeout = dask.config.get("simsvc.model.timeout", None)

def worker_callback():
    from model.fmu_unpack import unpack_model
    unpack_model(fmu_file)

@dask.delayed
def task(spec, cancel):
    # Relative import does not work here.
    try:
        from model.custom import process_results
    except ImportError:
        from model.util import serialise_results as process_results
    from model.fmu_unpack import fmu
    t0 = t1 = None
    pars = {}
    unk = []
    warn = ""
    for k, v in spec.inputs.items():
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
                             start_values=pars, timeout=timeout)
    return process_results(recs, {'warnings': warn})
