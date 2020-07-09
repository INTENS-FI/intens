#!/usr/bin/python3
# Simple synchronous client for the simulation service.
# Based on the requests library.

import requests, time
from threading import Condition
import socketio
from urllib.parse import urljoin, urlparse
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

class SimsvcClient:
    def __init__(self, service_url, timeout_sec=60):
        super().__init__()
        self.service_url = endslash(service_url)
        self.timeout_sec = timeout_sec
        self.session = requests.Session()
        self.watched = set()
        self.job_terminated = Condition()
        self.sio = socketio.Client()
        self.sio.on('terminated', self.on_terminated)
        path = urlparse(self.service_url)[2].rstrip("/") + "/socket.io"
        self.sio.connect(self.service_url, socketio_path=path)

    def on_terminated(self, arg):
        """Socket.IO termination event handler.

        If the terminating job is in watched, remove it and notify all on
        job_terminated, which is held for the whole operation.
        """
        job = arg['job']
        with self.job_terminated:
            try:
                self.watched.remove(job)
            except KeyError:
                pass
            else:
                self.job_terminated.notify_all()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def close(self):
        self.session.close()
        self.sio.disconnect()

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
        timestep = 30.0
        max_timestep = 30.0
        self.watched.add(jobid)
        while True:
            status = self.get_job_status(jobid)
            complete = is_completed(status)
            if complete:
                self.watched.discard(jobid)
                return status
            with self.job_terminated:
                #XXX As long as other watched jobs keep getting done, this can
                # loop forever.
                while (jobid in self.watched
                       and self.job_terminated.wait(timestep)):
                    pass
            timestep = min(2 * timestep, max_timestep)

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

if __name__ == '__main__':
    import argparse, json, sys
    p = argparse.ArgumentParser(
        description="Run a job on the simultion service",
        epilog="If both -f and -d are given, they are merged"
               " with -d taking precedence")
    p.add_argument('-f', '--file', default=None,
                   help="File with job inputs as a JSON object")
    p.add_argument('-d', '--data', metavar="JSON", default=None,
                   help="Job inputs as a JSON object")
    p.add_argument(
        'url', nargs='?', default="http://localhost:8080/",
        help="Simsvc base URL, default %(default)s")
    args = p.parse_args()
    if args.file:
        with open(args.file) as f:
            d = json.load(f)
    else:
        d = {}
    if args.data:
        d.update(json.loads(args.data))
    with SimsvcClient(args.url) as cli:
        st, res = cli.run_job(d)
    if st:
        print(json.dumps(res))
    else:
        print("Simulation terminated with error:\n", res, file=sys.stderr)
        sys.exit(1)
