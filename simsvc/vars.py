"""Requests for managing inputs and results.
"""

from flask import Blueprint, jsonify, request
import werkzeug.exceptions as wexc

import db, util

get_vars = Blueprint('get_vars', __name__)
set_vars = Blueprint('set_vars', __name__)

def _get_vars(st, vtype, job=None):
    if vtype == 'default':
        return st.default
    else:
        try:
            j = st.jobs[job]
        except KeyError as e:
            raise wexc.NotFound() from e
        if vtype == 'inputs':
            return j.inputs
        elif vtype == 'results':
            return j.results
        else:
            raise ValueError("Invalid vtype")

@get_vars.route('')
def get_all_vars(vtype, job):
    with db.transact() as conn:
        vars = _get_vars(db.get_state(conn), vtype, job)
        return jsonify(dict(vars))

@get_vars.route('/<var>')
def get_var(vtype, job, var):
    try:
        with db.transact() as conn:
            vars = _get_vars(db.get_state(conn), vtype, job)
            return jsonify(vars[var])
    except KeyError as e:
        raise wexc.NotFound() from e

@set_vars.route('', methods=['PUT'])
def set_all_vars():
    req = request.get_json()
    if not isinstance(req, dict):
        raise wexc.UnsupportedMediaType("Not a JSON object")
    with db.transact("set_all_vars") as conn:
        st = db.get_state(conn)
        vars = st.default
        vars.clear()
        vars.update(req)
        return util.empty_response

@set_vars.route('/<var>', methods=['PUT', 'DELETE'])
def set_var(var):
    meth = request.method
    try:
        with db.transact("set_var") as conn:
            st = db.get_state(conn)
            vars = st.default
            if meth == 'DELETE':
                del vars[var]
            else:
                val = request.get_json()
                if val is None:
                    raise wexc.UnsupportedMediaType("Not JSON data")
                vars[var] = val
            return util.empty_response
    except KeyError as e:
        raise wexc.NotFound() from e
