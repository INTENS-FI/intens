from .pareto import pick_pareto_front
from .hypervolume import hypervolume
import numpy as np
import pandas as pd
import sys

if __name__ == "__main__":
    m = pd.read_csv(sys.argv[1])
    objs = []
    refs = []
    for s in sys.argv[2:]:
        f = s.split(':')
        assert len(f) == 2
        objs.append(f[0])
        refs.append(float(f[1]))
    ref = np.array(refs)
    all_points = m[objs].to_numpy()

    pareto = pick_pareto_front(all_points)
    offsets = ref - pareto
    offsets = offsets[np.all(offsets > 0.0, axis=1), :]
    print(hypervolume(offsets))
