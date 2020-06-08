#!/usr/bin/python3
# Call functions of SimsvcClient and perform some sanity checks on the results.
# Covers all functions except get_job_file at least once.
# Requires a running simsvc-mpt service. The url is given on the command line.

from simclient import SimsvcClient, JobStatus
import numpy.random

import argparse
p = argparse.ArgumentParser()
p.add_argument('-n', metavar='N', type=int, default=20,
               help="portfolio size (default %(default)s)")
p.add_argument('url', help="Simsvc base URL")
args = p.parse_args()

numpy.random.seed(1)
mean = numpy.random.normal(size=args.n).tolist()
cov = numpy.random.normal(size=(args.n, args.n)).tolist()
weights1 = numpy.random.normal(size=args.n).tolist()
weights2 = numpy.random.normal(size=args.n).tolist()
weights3 = numpy.random.normal(size=args.n).tolist()

with SimsvcClient(args.url) as client:

    def check_defaults():
        assert set(client.get_default_keys()) == set(['cov', 'mean'])
        assert client.get_default_value('cov') == cov
        assert client.get_default_value('mean') == mean
        dvalues = client.get_default_values()
        assert dvalues['cov'] == cov
        assert dvalues['mean'] == mean
        dvalues = client.get_default_values(['cov', 'mean']) 
        assert dvalues['cov'] == cov
        assert dvalues['mean'] == mean
        assert client.get_default_values(['cov'])['cov'] == cov
        assert client.get_default_values(['mean'])['mean'] == mean

    client.put_default_values({'cov': cov, 'mean': mean})
    check_defaults()
    client.put_default_value('cov', cov)
    client.put_default_value('mean', mean)
    check_defaults()

    assert len(client.get_job_ids()) == 0
    assert len(client.get_job_statuses()) == 0

    inputs1 = {'c.w' : weights1}
    i = client.post_job(inputs1)
    assert set(client.get_job_ids()) == set([i])

    inputs2 = {'c.w' : weights2}
    j = client.post_job(inputs2)
    assert set(client.get_job_ids()) == set([i, j])
    assert set(client.get_job_statuses()) == set([i, j])
    assert set(client.get_job_statuses([i, j])) == set([i, j])
    assert set(client.get_job_statuses([i])) == set([i])
    assert set(client.get_job_statuses([j])) == set([j])

    jstat = client.get_job_statuses([i, j])
    #XXX GET /jobs?status=true seems to return string keys unlike GET /jobs
    assert jstat[i] in JobStatus
    assert jstat[j] in JobStatus
    assert len(jstat) == 2

    inputs3 = {'c.w' : weights3}
    k = client.post_job(inputs3)

    assert set(client.get_job_ids()) == set([i, j, k])
    assert set(client.get_job_statuses()) == set([i, j, k])
    assert set(client.get_job_statuses([i, j])) == set([i, j])
    assert set(client.get_job_statuses([i])) == set([i])
    assert set(client.get_job_statuses([j])) == set([j])

    def check_inputs(id, w):
        ivs = client.get_job_input_values(id)
        assert set(ivs) == set(['c.w', 'cov', 'mean'])
        assert ivs['c.w'] == w
        assert ivs['cov'] == cov
        assert ivs['mean'] == mean
        assert client.get_job_input_value(id, 'c.w') == w
        assert client.get_job_input_value(id, 'mean') == mean
        assert client.get_job_input_value(id, 'cov') == cov
        ivs2 = client.get_job_input_values(id, ['c.w'])
        assert set(ivs2) == set(['c.w'])
        assert ivs2['c.w'] == w

    def check_results(id):
        keys = ['c.norm', 'c.er', 'c.var']
        r1 = client.get_job_result_values(id)
        assert set(r1) == set(keys)

        r2 = client.get_job_result_values(id, keys)
        assert r1 == r2

        r3 = client.get_job_result_values(id, ['c.er', 'c.var'])
        assert set(r3) == set(['c.er', 'c.var'])
        assert r3['c.er'] == r1['c.er']
        assert r3['c.var'] == r1['c.var']

        assert r1['c.norm'] == client.get_job_result_value(id, 'c.norm')
        assert r1['c.er'] == client.get_job_result_value(id, 'c.er')
        assert r1['c.var'] == client.get_job_result_value(id, 'c.var')

        assert client.get_job_error(id) is None
        return r1

    client.wait_for_job(i)
    assert client.get_job_status(i) == JobStatus.DONE
    check_results(i)

    client.wait_for_job(j)
    assert client.get_job_status(j) == JobStatus.DONE
    res2 = check_results(j)

    client.wait_for_job(k)
    assert client.get_job_status(k) == JobStatus.DONE
    check_results(k)

    check_inputs(i, weights1)
    check_inputs(j, weights2)
    check_inputs(k, weights3)

    assert client.get_job_dir(k) == []
    assert client.get_job_dir(k, '') == []

    #NOT TESTED: client.get_job_file(k, path)

    client.delete_job(j)
    assert set(client.get_job_ids()) == set([i, k])
    assert set(client.get_job_statuses()) == set([i, k])
    assert set(client.get_job_statuses([i, j])) == set([i])
    assert set(client.get_job_statuses([i])) == set([i])
    assert set(client.get_job_statuses([j])) == set()

    success2b, detail2b = client.run_job(inputs2)
    assert success2b
    assert res2 == detail2b
    assert set(client.get_job_ids()) == set([i, k])

    client.delete_all_jobs()
    assert len(client.get_job_ids()) == 0
    assert len(client.get_job_statuses()) == 0
