"""A subprocess test model.
Just computes x + y but does it in a shell script with expr.
"""

from concurrent.futures import CancelledError
import os, subprocess as sp, traceback as tb

import dask

def run_it(spec):
    #TODO
    script = os.path.join(os.path.dirname(__file__), "sum.sh")
    return sp.Popen(
        [script] + [str(spec.inputs[n]) for n in ['x', 'y']],
        cwd=spec.workdir, stdin=sp.DEVNULL, stdout=sp.PIPE, stderr=sp.PIPE,
        universal_newlines=True)

def main(spec, cancel):
    out = err = None
    with run_it(spec) as proc:
        while True:
            if cancel.get():
                raise CancelledError("Cancelled by request")
            try:
                out, err = proc.communicate(timeout=5)
            except sp.TimeoutExpired:
                continue
            if proc.returncode:
                raise RuntimeError(
                    ("Subprocess exited with status %s. stdout:\n%s\n"
                     + "stderr:\n%s") % (proc.returncode, out, err))
            else:
                return {"sum": int(out), "warnings": err}

@dask.delayed
def task(spec, cancel):
    try:
        return main(spec, cancel)
    except:
        tb.print_exc()
        raise
