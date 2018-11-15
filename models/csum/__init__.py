"""Another subprocess test model.

Computes c.x + c.y (dotted names for Cityopt compatibility) with
an external program using the only scripting language that we can trust
to be available on every platform: Python.

Some o4j_client unit tests require a server with this model at the URL
specified in o4j_client/src/test/resources/test_model.yaml.
"""

from concurrent.futures import CancelledError
import sys, os, subprocess as sp, traceback as tb

import dask

def run_it(spec):
    #TODO
    script = os.path.join(os.path.dirname(__file__), "script.py")
    return sp.Popen(
        [sys.executable, script]
        + [str(spec.inputs[n]) for n in ['c.x', 'c.y']],
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
                return {"c.sum": int(out), "c.warnings": err}

@dask.delayed
def task(spec, cancel):
    try:
        return main(spec, cancel)
    except:
        tb.print_exc()
        raise
