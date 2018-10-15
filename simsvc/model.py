"""A mock model for simulator server testing.
"""

import operator as op

from dask import delayed

def task(inputs):
    return delayed(lambda x, y: {"sum": x + y})(inputs['x'], inputs['y'])
