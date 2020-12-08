import yaml, dragonfly, logging, pickle, numpy, pandas
from dragonfly.exd.exd_utils import EVAL_ERROR_CODE
from argparse import ArgumentParser, Namespace
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth

from .client import SimsvcClient
from . import cityopt, co2df

def prior_means(op):
    """Return a list of functions for computing objective means.

    The list contains None for objectives with no available prior.  op is
    a cityopt.OptProb.
    """
    raise NotImplementedError("Priors not yet implemented")

if __name__ == '__main__':
    logging.basicConfig()
    p = ArgumentParser(
        description="Bayesian optimisation with Dragonfly and Simsvc")
    p.add_argument('simsvc', type=str,
                   help="Simsvc URL or model YAML file")
    p.add_argument('problem', type=str,
                   help="Optimisation problem file in Cityopt CSV format")
    p.add_argument('-p', '--parallel', metavar='P', type=int, default=16,
                   help="number of parallel evaluations (default %(default)s)")
    p.add_argument('-t', '--timelimit', metavar='T', type=int, default=600,
                   help="time limit in seconds (default %(default)s)")
    p.add_argument('--use-prior', action='store_true',
                   help="use prior mean function")
    a = p.parse_args()
    if urlparse(a.simsvc).scheme:
        url = a.simsvc
        auth = None
    else:
        with open(a.simsvc) as f:
            y = yaml.safe_load(f)
        url = y['url']
        ya = y.get('auth')
        auth = HTTPBasicAuth(ya['username'], ya['password']) if ya else None
    op = cityopt.read_op(a.problem)
    cfg = co2df.load_config_dict(
        {'name': "simsvc", 'domain': co2df.df_domain(op)})
    opt = Namespace()
    opt.moors_scalarisation = 'linear'
    if a.use_prior:
        options.moo_gpb_prior_means = priors(op)

    obj = co2df.objective(op, cfg, url, auth=auth)
    n_objectives = obj[1]
    obj_directions = [sn for sn, expr in op.obj.values()]
    arg_names = list(op.dv)
    obj_names = list(op.obj)

    pareto_values, pareto_points, history = \
        dragonfly.multiobjective_maximise_functions(
            obj, None, a.timelimit,
            worker_manager='multiprocessing', num_workers=a.parallel,
            capital_type='realtime', config=cfg, options=opt)

    print("\nPareto values:")
    print(pareto_values)

    print("\nPareto points:")
    print(pareto_points)

    with open('debug.pickle', 'wb') as f:
        pickle.dump((pareto_points, pareto_values, history),
                    f, pickle.HIGHEST_PROTOCOL)

    no_result = [numpy.nan] * n_objectives
    query_values = [val if val != EVAL_ERROR_CODE else no_result
                    for val in history.query_vals]
    query_points = history.query_points_raw

    # restore correct signs
    pareto_values = numpy.array(pareto_values) * obj_directions
    query_values = numpy.array(query_values) * obj_directions

    queries = pandas.concat([
        pandas.DataFrame(data=query_points, columns=arg_names),
        pandas.DataFrame(data=query_values, columns=obj_names)
    ], 1)
    pareto = pandas.concat([
        pandas.DataFrame(data=pareto_points, columns=arg_names),
        pandas.DataFrame(data=pareto_values, columns=obj_names)
    ], 1)
    def match_pareto_row(q):
        return pandas.DataFrame.any(pandas.DataFrame.all(pareto == q, 1))
    queries['pareto'] = queries.apply(match_pareto_row, 1)

    if queries.pareto.sum() != len(pareto):
        logging.warn("Expected %s pareto points, matched %s",
                     queries.pareto.sum(), len(pareto))

    queries['acq'] = history.query_acqs
    queries['eval_time'] = history.query_eval_times
    queries['send_at'] = history.query_send_times
    queries['receive_at'] = history.query_receive_times

    queries.to_csv('queries.csv', index=False)
