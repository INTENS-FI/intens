"""A simple portfolio model for optimization client testing.
"""

from concurrent.futures import CancelledError

import dask, numpy as np

@dask.delayed
def task(spec, cancel):
    if cancel.get():
        raise CancelledError("Cancelled by request")
    cov = np.array(spec.inputs['cov'])
    mean = np.array(spec.inputs['mean'])
    w = np.array(spec.inputs['c.w'])
    z = max(0.5, sum(w))
    w /= z
    return {'c.norm': z, 'c.er': mean @ w, 'c.var': w @ cov @ w}
