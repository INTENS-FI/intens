#!/usr/bin/python3
# Simple synchronous client for the simulation service.
# Based on the requests library.

import requests, time
from urllib.parse import urljoin
from enum import Enum

if False:
    # Logging for debug purposes
    import logging
    from http.client import HTTPConnection
    HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

if True:
    # Monkey-patch urllib3 to ignore spurious "Transfer-Encoding: chunked" for
    # responses that are supposed to be bodyless according to HTTP status code
    import urllib3
    def _init_length(self, request_method):
        try:
            self.bodyless = (self.status in (204, 304)
                             or 100 <= self.status < 200
                             or request_method == "HEAD")
        except ValueError:
            self.bodyless = False
        return self._init_length_UNPATCHED(request_method)

    def stream(self, amt=2 ** 16, decode_content=None):
        if not self.bodyless:
            yield from self.stream_UNPATCHED(amt, decode_content)

    setattr(urllib3.HTTPResponse, '_init_length_UNPATCHED',
            urllib3.HTTPResponse._init_length)
    setattr(urllib3.HTTPResponse, '_init_length', _init_length)

    setattr(urllib3.HTTPResponse, 'stream_UNPATCHED',
            urllib3.HTTPResponse.stream)
    setattr(urllib3.HTTPResponse, 'stream', stream)


JobStatus = Enum('JobStatus',
                 'SCHEDULED RUNNING DONE CANCELLED FAILED INVALID')

def is_completed(status):
    return status != JobStatus.SCHEDULED and status != JobStatus.RUNNING

def endslash(url):
    return url if (len(url) > 0 and url[-1] == '/') else url + '/'

class SimsvcClient(object):
    def __init__(self, service_url, timeout_sec=60):
        super().__init__()
        self.service_url = endslash(service_url)
        self.timeout_sec = timeout_sec
        self.session = requests.Session()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def close(self):
        self.session.close()

    def _join_url(self, *parts):
        return urljoin(self.service_url, '/'.join(map(str, parts)))

    def _get(self, url):
        r = self.session.get(url, timeout=self.timeout_sec)
        r.raise_for_status()
        return r

    def _get_dict(self, url, keys):
        url = endslash(url)
        if keys is None:
            r = self.session.get(url, params={'values': 'true'},
                                 timeout=self.timeout_sec)
        else:
            r = self.session.get(url, params={'only': ",".join(keys)},
                                 timeout=self.timeout_sec)
        r.raise_for_status()
        return r.json()

    def _put_json(self, url, value):
        r = self.session.put(url, json=value, timeout=self.timeout_sec)
        r.raise_for_status()

    def _delete(self, url):
        r = self.session.delete(url, timeout=self.timeout_sec)
        r.raise_for_status()


    def get_default_keys(self):
        return self._get(self._join_url('default/')).json()

    def get_default_values(self, keys=None):
        return self._get_dict(self._join_url('default'), keys)

    def get_default_value(self, key):
        return self._get(self._join_url('default', key)).json()

    def put_default_values(self, default_dict):
        self._put_json(self._join_url('default/'), default_dict)

    def put_default_value(self, key, value):
        self._put_json(self._join_url('default', key), value)

    def get_job_ids(self):
        return self._get(self._join_url('jobs/')).json()

    def get_job_statuses(self, jobids=None):
        url = self._join_url('jobs/')
        if jobids is None:
            r = self.session.get(
                url, params={'status': 'true'}, timeout=self.timeout_sec)
        else:
            r = self.session.get(
                url, params={'status': 'true',
                             'only': ",".join(map(str, jobids))},
                timeout=self.timeout_sec)
        r.raise_for_status()
        return dict((int(k), JobStatus[v]) for k,v in r.json().items())

    def post_job(self, inputs_dict):
        r = self.session.post(self._join_url('jobs/'),
                              json=inputs_dict, timeout=self.timeout_sec)
        r.raise_for_status()
        if r.status_code != requests.codes.created:
            raise Exception('Unexpected status ' + r.status_code)
        return r.json()

    def delete_all_jobs(self):
        self._delete(self._join_url('jobs/'))

    def get_job_status(self, jobid):
        return JobStatus[self._get(self._join_url('jobs', jobid)).json()]

    def delete_job(self, jobid):
        self._delete(self._join_url('jobs', jobid))

    def get_job_input_values(self, jobid, keys=None):
        return self._get_dict(self._join_url('jobs', jobid, 'inputs'), keys)

    def get_job_input_value(self, jobid, key):
        return self._get(self._join_url('jobs', jobid, 'inputs', key)).json()

    def get_job_error(self, jobid):
        return self._get(self._join_url('jobs', jobid, 'error')).json()

    def get_job_result_values(self, jobid, keys=None):
        return self._get_dict(self._join_url('jobs', jobid, 'results'), keys)

    def get_job_result_value(self, jobid, key):
        return self._get(self._join_url('jobs', jobid, 'results', key)).json()

    def get_job_file(self, jobid, path):
        return self._get(self._join_url('jobs', jobid, 'files', path)).content

    def get_job_dir(self, jobid, path=''):
        return self._get(self._join_url('jobs', jobid, 'dir', path)).json()

    def wait_for_job(self, jobid):
        timestep = 0.1
        max_timestep = 10.0
        status = self.get_job_status(jobid)
        complete = is_completed(status)
        while not complete:
            time.sleep(timestep)
            timestep = min(2 * timestep, max_timestep)
            status = self.get_job_status(jobid)
            complete = is_completed(status)
        return status

    def run_job(self, inputs_dict):
        jobid = self.post_job(inputs_dict)
        try:
            status = self.wait_for_job(jobid)
            if status == JobStatus.DONE:
                return (True, self.get_job_result_values(jobid))
            else:
                return (False, self.get_job_error(jobid))
        finally:
            self.delete_job(jobid)
