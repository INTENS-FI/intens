"""A mock model for simulator server testing.
"""

from concurrent.futures import CancelledError

import dask

@dask.delayed
def task(inputs, canc):
    if canc.get():
        raise CancelledError("Cancelled by request")
    return {"sum": inputs['x'] + inputs['y']}
