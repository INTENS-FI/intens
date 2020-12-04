"""Solve Cityopt problems with Dragonfly.

Requires dragonfly-opt
"""

import logging

from dragonfly.parse.config_parser import load_parameters
from dragonfly import load_config

from .cityopt import Type

logging.basicConfig()

def load_config_dict(d):
    """Load Dragonfly config from dict d.

    d should be what you'd normally put in a JSON file, i.e., 
    with open(fn) as f: load_config_dict(json.load(f)) is equivalent
    to dragonfly.load_config_file(fn).  This function is useful when d
    does not come directly from a file.
    """
    return load_config(load_parameters(d))

type_map = {Type.INT: "int", Type.FLOAT: "float"}

def gen_df_domain(op):
    """Generate Dragonfly domain config from cityopt.OptProb.

    Like df_domain but generates (key, value) pairs.
    """
    for n, (ty, lb, ub) in op.dv.items():
        yield n, {"name": n, "type": type_map[ty], "min": lb, "max": ub}

def df_domain(op):
    """Convert cityopt.OptProb into Dragonfly domain config.

    The result can be entered as 'domain' into a dict that is then
    passed to load_config_dict.
    """
    return dict(gen_df_domain(op))

def objective(op, config, client, n_retries=0):
    """Return an objective function for Dragonfly.
    
    op is a cityopt.OptProb, config a Dragonfly config and client
    a SimsvcClient.  Returns a pair that can be passed as funcs to
    dragonfly.multiobjective_maximise_functions.  If evaluation fails,
    it is retried n_retries times or until success.
    """
    dvs = config.domain_orderings.raw_name_ordering
    senses = [sn for sn, expr in op.obj.values()]
    def fun(*args):
        assert len(dvs) == len(args)
        loc = op.make_locals()
        inp = dict(gen_in(loc, zip(dvs, args)))
        for i in range(n_retries + 1):
            try:
                ok, res = client.run_job(inp, delete=False)
            except:
                logging.exception("SimsvcClient.run_job failed")
                res = None
            else:
                if ok:
                    break
                else:
                    logging.error("Job failed: %s", res)
            if i < n_retries:
                print("  retrying...")
        if ok:
            op.eval_met(loc, res)
            obj = dict(op.gen_obj(loc))
            print(" ", *(" {}={:.5g}".format(k, v) for k, v in zip(dvs, args)))
            print(" ", *(" {}={:.5g}".format(k, v) for k, v in obj.items()))
            return tuple(sn * v for sn, v in zip(senses, obj.values()))
        else:
            logging.error("Run failed: {}; inputs={}", result, inputs)
            return dragonfly.exd.exd_utils.EVAL_ERROR_CODE
    return fun, len(op.obj)
