import numpy as np

def pick_pareto_front(points, keep_equal=False):
    """Returns the Pareto-optimal points from a set of points,
    assuming all objectives are minimisation objectives.

    The n points in d-dimensional objective space are given in an ndarray
    of shape (n,d), and the return value is of shape (m,d) where m is the
    number of Pareto-optimal points.

    If keep_equal is False, equal points are pruned so that only one of them
    is returned.
    """
    pareto = flag_pareto_front(points, keep_equal)
    return points[pareto,:]

def flag_pareto_front(points, keep_equal=False):
    """Determines which points are Pareto-optimal,
    assuming all objectives are minimisation objectives.

    The n points in d-dimensional objective space are given in an ndarray
    of shape (n,d). The return value is a boolean ndarray of length n,
    where True indicates Pareto-optimal points.

    If keep_equal is False, equal points are pruned so that only one of them
    is selected.
    """
    n_points = points.shape[0]
    pareto = np.ones(n_points, dtype=bool)
    for i in range(n_points):
        if pareto[i]:
            # points[i] is not dominated by any earlier points.
            # Clear the flag on points dominated by points[i], or
            # optionally equal to it.
            if keep_equal:
                pareto[pareto] = (np.any(points[pareto] < points[i], axis=1) |
                                  np.all(points[pareto] == points[i], axis=1))
            else:
                pareto[pareto] = np.any(points[pareto] < points[i], axis=1)
                pareto[i] = True
    return pareto
