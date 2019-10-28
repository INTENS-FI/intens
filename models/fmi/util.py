"""FMI support utilities
"""

def serialise_results(recs, out=None):
    """Convert FMPy simulation results to a JSON serialisable form.

    Returns a JSON serialisable dict.  If out is given, new items are
    added to it (values already there should be serialisable),
    otherwise a fresh dict is created.  recs is a sturctured Numpy
    array with a field 'time'.  Its other fields are interpreted as
    time series using 'time' as the coordinate variable.  All fields
    are converted to tuples (ZODB likes tuples because they are
    immutable).
    """
    res = {} if out is None else out
    res['time'] = tuples(recs['time'])
    res.update((k, {'times': 'time', 'values': tuples(recs[k])})
               for k in res.dtype.names if k != 'time')
    return res
