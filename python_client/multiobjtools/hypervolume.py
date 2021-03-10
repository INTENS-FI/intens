import numpy as np

def hypervolume(ps):
    """Compute hypervolume of the union of n boxes in d-dimensional space.
    The dimensions of the boxes are given in an array of shape (n,d).
    All dimensions must be positive.  Returns the hypervolume as a scalar.

    The function is not fast: runtime is proportional to n**d.
    Selecting the pareto-optimal points first is recommended.
    """
    n,d = ps.shape
    axes = [np.unique(ps[:,i]) for i in range(d)]

    # (d, ...) - grid point coordinates
    grid_full = np.array(np.meshgrid(*axes, indexing='ij'))

    # (d, m) - grid point coordinates
    grid_flat = grid_full.reshape((d, -1))

    # (n, m) - which grid point q is within which box of input point p
    p_ge_q = np.all(grid_flat[np.newaxis,:,:] <= ps[:,:,np.newaxis], axis=1)

    # (m,) - which grid point q is within the input hypervolume
    q_in = np.any(p_ge_q, axis=0)

    # grid box volumes
    vol = np.prod([np.diff(grid_full[i,:], prepend=0.0, axis=i)
                   for i in range(d)],
                  axis=0)
    # sum the volumes of the active grid boxes
    return np.dot(q_in, np.ravel(vol))


if __name__ == "__main__":
    import unittest
    class TestHypervolume(unittest.TestCase):
        def test1_1(self):
            self.assertEqual(hypervolume(np.array([[2]])), 2.0)
        def test1_2(self):
            self.assertEqual(hypervolume(np.array([[2],[1]])), 2.0)
        def test2_1(self):
            self.assertEqual(hypervolume(np.array([[1,1]])), 1.0)
        def test2_2a(self):
            self.assertEqual(hypervolume(np.array([[1,2],[2,1]])), 3.0)
        def test2_2b(self):
            self.assertEqual(hypervolume(np.array([[1,2],[3,1]])), 4.0)
        def test2_3a(self):
            self.assertEqual(hypervolume(np.array([[1,2],[2,1],[2,2]])), 4.0)
        def test2_3b(self):
            self.assertEqual(hypervolume(np.array([[1,2],[3,1],[2,2]])), 5.0)
        def test2_3c(self):
            self.assertEqual(hypervolume(np.array([[1,3],[3,1],[2,2]])), 6.0)
        def test2_3d(self):
            self.assertEqual(hypervolume(np.array([[1,3],[3,1],[3,2]])), 7.0)
        def test3_1a(self):
            self.assertEqual(hypervolume(np.array([[1,1,2]])), 2.0)
        def test3_2a(self):
            self.assertEqual(hypervolume(np.array([[1,1,2],[2,1,1]])), 3.0)
        def test3_2b(self):
            self.assertEqual(hypervolume(np.array([[1,1,1],[2,1,1]])), 2.0)
        def test3_2c(self):
            self.assertEqual(hypervolume(np.array([[2,2,2],[3,1,1]])), 9.0)
        def test3_3a(self):
            self.assertEqual(hypervolume(np.array([[2,2,2],[3,1,1],[1,4,1]])), 11.0)
        def test3_4a(self):
            self.assertEqual(hypervolume(np.array([[1,1,5],[2,2,2],[3,1,1],[1,4,1]])), 14.0)

    unittest.main()
