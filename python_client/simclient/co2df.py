"""Solve Cityopt problems with Dragonfly.

Requires dragonfly-opt.  Constraints are ignored!
"""

import logging, numpy as np, sys

from dragonfly.parse.config_parser import load_parameters
from dragonfly import load_config
from dragonfly.exd.exd_utils import EVAL_ERROR_CODE
from dragonfly.exd.cp_domain_utils import get_raw_point_from_processed_point

from .cityopt import Type, Component
from .client import SimsvcClient

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

def _fix_type(x):
    return int(x) if isinstance(x, np.signedinteger) else x

def objective(op, config, url, auth=None, n_retries=0):
    """Return an objective function for Dragonfly.
    
    op is a cityopt.OptProb, config a Dragonfly config.  url and auth are
    passed to SimsvcClient.  Returns a pair that can be passed as funcs to
    dragonfly.multiobjective_maximise_functions.  If evaluation fails,
    it is retried n_retries times or until success.
    """
    dvs = config.domain_orderings.raw_name_ordering
    senses = [sn for sn, expr in op.obj.values()]
    def fun(args):
        assert len(dvs) == len(args)
        loc = op.make_locals()
        inp = dict(op.gen_in(loc, zip(dvs, (_fix_type(a) for a in args))))
        #XXX It is stupid to create a client per call but hard to do
        # better with Dragonfly, because it uses multiple processes, not
        # threads.  Can't really blame it, considering the sorry state
        # of threading in CPython.  We could use the ask-tell API instead
        # but I can't find if it works for MOO, probably not.  Or implement
        # our own worker manager, which also looks hairy.
        ok = False
        with SimsvcClient(url, auth) as client:
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
            logging.error("Run failed: {}; inputs={}", res, inp)
            return EVAL_ERROR_CODE
    # Dragonfly silently swallows all exceptions thrown by the objective
    # function.  Nasty to debug.  We aren't having that.
    def foo(args):
        try:
            return fun(args)
        except:
            logging.exception("Exception in objective function")
            sys.exit(1)
    return foo, len(op.obj)

def _make_prior_mean_obj(op, config, n):
    dvs = config.domain_orderings.raw_name_ordering
    sn,_ = op.obj[n]
    def fun(processed_point):
        args = get_raw_point_from_processed_point(
            processed_point, config.domain,
            config.domain_orderings.index_ordering,
            config.domain_orderings.dim_ordering)
        assert len(dvs) == len(args)
        loc = op.make_locals()
        inp = dict(op.gen_in(loc, zip(dvs, (_fix_type(a) for a in args))))
        #TODO op.eval_met without result
        return sn * op.eval_obj(n, loc)
    def wrap(args):
        try:
            return np.array([fun(point) for point in args])
        except:
            logging.exception(
                f"Exception in prior objective function {n} with args={args}")
            sys.exit(1)
    return wrap

def prior_means(op, config):
    """Return a list of functions for computing objective means.

    The list contains None for objectives with no available prior.  op is
    a cityopt.OptProb, config a Dragonfly config.
    """
    prior_flags = op.flag_prior_objs()
    logging.info("Setting up prior means for: " + " ".join(
        n for f,n in zip(prior_flags, op.obj.keys()) if f))
    return [_make_prior_mean_obj(op, config, n) if f else None
            for f,n in zip(prior_flags, op.obj.keys())]

def tabulate_job_data(op, url, auth=None):
    """Read job inputs and outputs from the service and compute metrics.
    Returns list of dictionaries, each dictionary mapping qualified names
    to values in a specific job.  If some jobs do not have sufficient data
    for the optimisation problem 'op', they are skipped (with a warning).
    """
    with SimsvcClient(url, auth) as client:
        jobdata = client.read_all_results()
    results = []
    for jobid, (jin, jout) in jobdata.items():
        loc = op.make_locals()
        try:
            loc.update(jin)
            op.eval_met(loc, jout)
            for _ in op.gen_obj(loc, update=True): pass
            results.append(dict((k, v) for k, v in loc.items()
                                if not isinstance(v, Component)))
        except Exception as e:
            logging.warning(f'Failed to evaluate job {jobid}: {str(e)}')
    return results

def args2inputs(op, args):
    loc = op.make_locals()
    return dict(op.gen_in(loc, ((n, _fix_type(args[n]))
                                for n in op.dv.keys())))
