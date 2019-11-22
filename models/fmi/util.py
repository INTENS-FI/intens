"""FMI support utilities
"""

import re

def sanitise(name):
    """Convert name into a valid identifier.
    """
    res = re.sub(r"\[(\d+)]$", r"_\1", name)
    res = re.sub(r"\W+", r"_", res)
    res = re.sub(r"^(\d)", r"_\1", res)
    return "o." + res

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
    res['time'] = tuple(recs['time'])
    res.update((sanitise(k), {'times': 'time', 'values': tuple(recs[k])})
               for k in recs.dtype.names if k != 'time')
    return res
