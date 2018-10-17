"""Requests for job management.
"""

from flask import Blueprint, jsonify, request, current_app, url_for
import werkzeug.exceptions as wexc
from http import HTTPStatus

import db, tasks, util

jobs_bp = Blueprint('jobs_bp', __name__)

@jobs_bp.route('/')
def get_jobs():
    wstat = request.args.get("status", type=util.boolstr)
    if wstat:
        tasks.refresh_jobs()
    with db.transact() as conn:
        st = db.get_state(conn)
        return jsonify({k: j.status.name for k, j in st.jobs.items()}
                       if wstat else list(st.jobs.keys()))

@jobs_bp.route('/<int:job>')
def get_job(job):
    tasks.refresh_jobs()
    with db.transact() as conn:
        j = db.get_state(conn).jobs[job]
        return jsonify(j.status.name)

@jobs_bp.route('/', methods=['POST'])
def post_job():
    req = request.get_json()
    if not isinstance(req, dict):
        raise wexc.UnsupportedMediaType("Not a JSON object")
    with db.transact("post_job") as conn:
        jid, j = db.create_job(conn, req)
        tasks.launch(jid, j)
    return jsonify(jid), HTTPStatus.CREATED, {
        "Location": url_for('.get_job', job=jid)}

@jobs_bp.route('/<int:job>', methods=['DELETE'])
def delete_job(job):
    with db.transact("delete_job") as conn:
        jobs = db.get_state(conn)
        j = st.jobs[job]
        old = j.status
        j.status = db.Job_status.CANCELLED
        if tasks.cancel(job, delete=True):
            return (jsonify("Cancelling, status was %s" % old.name),
                    HTTPStatus.ACCEPTED)
        elif j.close():
            del st.jobs[job]
            return util.empty_response
        else:
            err = j.error
    # Let's be careful - jsonify(err) might raise.
    return jsonify(err), HTTPStatus.INTERNAL_SERVER_ERROR

@jobs_bp.route('/', methods=['DELETE'])
def delete_all_jobs():
    with db.transact("delete_all_jobs") as conn:
        jobs = db.get_state(conn).jobs
        ntot = len(jobs)
        ncanc = 0
        nerr = 0
        for jid, job in list(jobs.items()):
            job.status = db.Job_status.CANCELLED
            if tasks.cancel(jid, delete=True):
                ncanc += 1
            elif job.close():
                del jobs[jid]
            else:
                nerr += 1
    return ((jsonify("Errors deleting %d/%d jobs" % (nerr, ntot)),
             HTTPStatus.INTERNAL_SERVER_ERROR) if nerr
            else (jsonify("%d/%d job deletions pending cancellation"
                          % (ncanc, ntot)),
                  HTTPStatus.ACCEPTED) if ncanc
            else jsonify("%d jobs deleted" % ntot))

@jobs_bp.route('/<int:job>/error')
def get_error(job):
    with db.transact() as conn:
        j = db.get_state(conn).jobs[job]
        return jsonify(j.error)
