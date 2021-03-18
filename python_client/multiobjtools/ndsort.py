"""Nondominated sorting (as in NSGA).
"""

import numpy as np
from numba import jit, njit

@njit
def doms(u, v):
    """Return -1 if u dominates v, 1 if v dominates u and 0 otherwise.

    u dominates v if all(u <= v) and any(u < v), i.e., in minimisation sense.
    """
    assert len(u) == len(v)
    sg = 0
    for ui, vi in zip(u, v):
        if ui == vi:
            continue
        s = -1 if ui < vi else 1
        if sg == 0:
            sg = s
        elif sg != s:
            return 0
    return sg

# Currently miscompiles.
# Try ndsort(np.arange(6).reshape((3, 2))).
#@jit
def ndsort(obj):
    """Non-dominated sorting.

    obj is a matrix.  Its rows are individuals and columns minimisation
    objectives.  Return a list of fronts with each front a list of row
    indices to obj.  Members of each front are not dominated by any member
    of the same or subsequent fronts but, apart from the first front, are
    dominated by some member of the preceding front.
    """
    # ss[i] are the solutions dominated by i.
    ss = [[] for r in obj]
    # ns[i] is the number of solutions that dominate i.
    ns = np.zeros(len(obj), dtype=np.uint)
    for i in range(len(obj) - 1):
        for j in range(i + 1, len(obj)):
            d = doms(obj[i], obj[j])
            if d == -1:
                ss[i].append(j)
                ns[j] += 1
            elif d == 1:
                ss[j].append(i)
                ns[i] += 1
    fs = []
    f = [i for i, n in enumerate(ns) if n == 0]
    while f:
        fs.append(f)
        nf = []
        for i in f:
            for j in ss[i]:
                ns[j] -= 1
                if ns[j] == 0:
                    nf.append(j)
        f = nf
    return fs

def domrank(n, fs):
    """Domination rank.

    Return a vector r of length n such that r[i] = j if i in fs[j].  r[i] = -1
    if i is not in any element of fs.  Elements of fs are assumed not to
    intersect.  fs is normally from ndsort.
    """
    rs = np.full(n, -1)
    for r, f in enumerate(fs):
        rs[f] = r
    return rs

@njit
def _ndfront(obj, front):
    for i in range(len(obj) - 1):
        if not front[i]:
            continue
        for j in range(i + 1, len(obj)):
            if not front[j]:
                continue
            d = doms(obj[i], obj[j])
            if d == -1:
                front[j] = False
            elif d == 1:
                front[i] = False

def ndfront(obj):
    """Non-dominated front.

    Return a boolean vector indicating the non-dominated objectives.
    ndfront(obj).nonzero()[0] is equivalent to ndsort(obj)[0] but faster
    (and returns an array).
    """
    front = np.ones(len(obj), dtype=bool)
    _ndfront(obj, front)
    return front
