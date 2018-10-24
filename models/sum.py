"""A mock model for simulator server testing.
"""

from concurrent.futures import CancelledError

import dask

@dask.delayed
def task(spec, cancel):
    if cancel.get():
        raise CancelledError("Cancelled by request")
    return {"sum": spec.inputs['x'] + spec.inputs['y']}
