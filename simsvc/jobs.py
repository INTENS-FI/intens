"""Requests for job management.
"""

from flask import Blueprint, jsonify, request, current_app, url_for
import werkzeug.exceptions as wexc
from http import HTTPStatus

import db, util

jobs_bp = Blueprint('jobs_bp', __name__)

@jobs_bp.route('')
def get_jobs():
    with db.transact() as conn:
        st = db.get_state(conn)
        return jsonify({k: j.status.name for k, j in st.jobs.items()}
                       if request.args.get("status", type=util.boolstr)
                       else list(st.jobs.keys()))

@jobs_bp.route('/<int:job>')
def get_job(job):
    with db.transact() as conn:
        j = db.get_state(conn).jobs[job]
        return jsonify(j.status.name)

@jobs_bp.route('', methods=['POST'])
def post_job():
    req = request.get_json()
    if not isinstance(req, dict):
        raise wexc.UnsupportedMediaType("Not a JSON object")
    with db.transact("post_job") as conn:
        jid, j = db.create_job(conn, req)
        #TODO Launch!
    return jsonify(jid), HTTPStatus.CREATED, {
        "Location": url_for('.get_job', job=jid)}

@jobs_bp.route('/<int:job>', methods=['DELETE'])
def delete_job(job):
    with db.transact("delete_job") as conn:
        st = db.get_state(conn)
        j = st.jobs[job]
        if j.status in [db.Job_status.SCHEDULED, db.Job_status.RUNNING]:
            j.status = db.Job_status.CANCELED
            #TODO Cancel and arrange for deletion on termination.
            return (jsonify("Canceling, status was %s" % j.status),
                    HTTPStatus.ACCEPTED)
        else:
            del st.jobs[job]
            return util.empty_response
