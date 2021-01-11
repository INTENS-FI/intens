import yaml, dragonfly, logging, pickle, numpy, pandas
from dragonfly.exd.exd_utils import EVAL_ERROR_CODE
from argparse import ArgumentParser, Namespace
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth

from .client import SimsvcClient
from . import cityopt, co2df

# Based on dragonfly/bin/dragonfly-script.py
def _make_df_options_parser():
    optlist = (
        dragonfly.opt.ga_optimiser.ga_opt_args
        + dragonfly.opt.gp_bandit.get_all_euc_gp_bandit_args()
        + dragonfly.opt.gp_bandit.get_all_cp_gp_bandit_args()
        + dragonfly.opt.gp_bandit.get_all_mf_euc_gp_bandit_args()
        + dragonfly.opt.gp_bandit.get_all_mf_cp_gp_bandit_args()
        + dragonfly.opt.random_optimiser.euclidean_random_optimiser_args
        + dragonfly.opt.random_optimiser.mf_euclidean_random_optimiser_args
        + dragonfly.opt.random_optimiser.cp_random_optimiser_args
        + dragonfly.opt.random_optimiser.mf_cp_random_optimiser_args
        + dragonfly.opt.multiobjective_gp_bandit.get_all_euc_moo_gp_bandit_args()
        + dragonfly.opt.multiobjective_gp_bandit.get_all_cp_moo_gp_bandit_args()
        + dragonfly.opt.random_multiobjective_optimiser.euclidean_random_multiobjective_optimiser_args
        + dragonfly.opt.random_multiobjective_optimiser.cp_random_multiobjective_optimiser_args)
    optdict = dict((o['name'] if o['name'].startswith('-') else '--'+o['name'],
                    dict((k,v) for k,v in o.items() if k != 'name'))
                   for o in optlist)
    p = ArgumentParser("Dragonfly options")
    for n,o in optdict.items():
        p.add_argument(n, **o)
    return p

def _find_row_index(rowtuple, df):
    rowflags = pandas.DataFrame.all(df == rowtuple, 1)
    ii = numpy.where(rowflags)[0]
    return -1 if len(ii) == 0 else ii[0]

if __name__ == '__main__':
    log_stderr = logging.StreamHandler()
    log_stderr.setLevel(logging.WARNING)
    log_file = logging.FileHandler("debug.log")
    logging.basicConfig(
        level=logging.DEBUG, handlers=[log_stderr, log_file],
        format='%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s'
    )
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
    p.add_argument('-D', '--option', action='append',
                   metavar='OPTION=VALUE', help="Dragonfly option setting")
    p.add_argument('-F', '--options-file', action='append',
                   help="Dragonfly options file")
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
    dfp = _make_df_options_parser()
    opt = Namespace()
    for path in a.options_file or []:
        with open(path) as f:
            dfp.parse_args([s for r in f for s in r.strip().split()], opt)
    for ov in a.option or []:
        o = ov.split('=', 1)
        o[0] = '--'+o[0]
        dfp.parse_args(o, opt)
    if a.use_prior:
        opt.moo_gpb_prior_means = co2df.prior_means(op, cfg)

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

    # Evaluate metrics using job data stored in the service.
    # Dragonfly queries are matched with jobs by input & objective values.
    met_names = list(op.met.keys())
    job_data = pandas.DataFrame(co2df.tabulate_job_data(op, url, auth=auth))
    query_io = pandas.DataFrame(
        pandas.concat([pandas.Series(co2df.args2inputs(op, row[arg_names])),
                       row[obj_names]])
        for _,row in queries.iterrows())
    job_io = job_data[query_io.columns]
    ri = numpy.array([_find_row_index(io, job_io)
                      for io in query_io.itertuples(False)])
    for n in met_names:
        queries[n] = job_data[n].iloc[ri].tolist()
    queries.loc[ri < 0, met_names] = numpy.nan

    queries.to_csv('queries.csv', index=False)
