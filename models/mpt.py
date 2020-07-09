"""A simple test model for optimization client.
Based on "modern" portfolio theory (Markowitz, 1952).

Inputs:
	cov	covariance between assets (positive semidefinite matrix)
	mean	expected return for each asset (vector)
	c.w	unnormalized portfolio weights (vector)
Outputs:
	c.norm	normalisation factor for portfolio weights (scalar)
	c.er	expected return of portfolio (scalar)
	c.var	variance of portfolio (non-negative scalar)

Random values for cov and mean can be generated with init-mpt.py.  c.w is
the decision variable; the objectives are to maximize c.er and minimize c.var.
Negative weights can be used for shorting.
"""

from concurrent.futures import CancelledError

import dask, numpy as np

@dask.delayed
def task(spec, cancel):
    if cancel.get():
        raise CancelledError("Cancelled by request")
    cov = np.array(spec.inputs['cov'])
    mean = np.array(spec.inputs['mean'])
    w = np.array(spec.inputs['c.w'], dtype=float)
    z = max(0.5, sum(w))
    w /= z
    return {'c.norm': z, 'c.er': mean @ w, 'c.var': w @ cov @ w}
