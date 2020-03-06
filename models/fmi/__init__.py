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
"""

import os, logging, multiprocessing as mp
import dask, fmpy

logger = logging.getLogger(__name__)

fmu_file = os.getenv("MODEL_FMU") or dask.config.get("simsvc.model.fmu",
                                                     "model.fmu")
simargs = dask.config.get("simsvc.model.simulate-fmu-args", {})
timeout = dask.config.get("simsvc.model.timeout", None)

def worker_callback():
    from model.fmu_unpack import unpack_model
    unpack_model(fmu_file)

def simulate_direct(fmu, t0, t1, pars):
    return fmpy.simulate_fmu(fmu, start_time=t0, stop_time=t1,
                             start_values=pars, **simargs)

class FMU_process(mp.Process):
    """Simulate FMU in a subprocess

    Useful if the FMU is prone to crashing or hanging.
    """
    def __init__(s, *args):
        super().__init__(daemon=True)
        s.args = args
        s.pout, s.pin = mp.Pipe(False)

    def run(s):
        from model.fmu_unpack import retain
        retain()
        s.pin.send(simulate_direct(*s.args))
        s.pin.close()

def simulate(*args):
    """Simulate FMU.

    If timeout is None, simulate directly.  Otherwise use a subprocess,
    kill it if timeout elapses and raise TimeoutError.  args are passed
    to simulate_direct, and its return value is returned.

    If running in a daemon process with a timeout, raise RuntimeError.
    """
    if timeout is None:
        return simulate_direct(*args)
    if mp.current_process().daemon:
        raise ValueError(
            "Cannot enforce timeout.  "
            "Try setting distributed.worker.daemon to false.")
    p = FMU_process(*args)
    p.start()
    if not p.pout.poll(timeout):
        p.terminate()
        raise RuntimeError("Timeout in FMU simulation")
    res = p.pout.recv()
    p.join()
    return res

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
    recs = simulate(fmu, t0, t1, pars)
    return process_results(recs, {'warnings': warn})
