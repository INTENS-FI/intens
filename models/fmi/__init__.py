"""FMI support for Simsvc.

This should be installed as package "model".  Behaviour can be
modified by adding a module "custom".  The following customisations
are currently available:

process_results(recs, out)	Read simulation results from the structured
	array recs and add them in JSON serialisable form to the dict out
	(with variable names as keys).  Return out.  Defaults to
	.util.serialise_results.
"""

import dask, fmpy

def worker_callback():
    from model.fmu_unpack import unpack_model
    unpack_model()

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
                             start_values=pars)
    return process_results(recs, {'warnings': warn})
