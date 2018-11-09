"""Requests for managing inputs and results.
"""

from enum import Enum

from flask import Blueprint, jsonify, request
import werkzeug.exceptions as wexc

from . import db, util

get_vars = Blueprint('get_vars', __name__)
set_vars = Blueprint('set_vars', __name__)

Vtype = Enum('Vtype', 'default inputs results')

def _get_vars(st, vtype=None, job=None):
    vt = Vtype.default if vtype is None else Vtype[vtype]
    if vt == Vtype.default:
        return st.default
    else:
        try:
            j = st.jobs[job]
        except KeyError as e:
            raise wexc.NotFound from e
        if vt == Vtype.inputs:
            return j.inputs
        elif vt == Vtype.results:
            return j.results
        else:
            raise ValueError("Unknown vtype %s" % vt)

@get_vars.route('/')
def get_all_vars(vtype, job):
    values = request.args.get("values", type=util.boolstr)
    only = request.args.get("only")
    if only is not None:
        only = [vn.strip() for vn in only.split(",")]
    try:
        with db.transact() as conn:
            vars = _get_vars(db.get_state(conn), vtype, job)
            return jsonify({k: vars[k] for k in only} if only
                           else dict(vars) if values else list(vars))
    except KeyError as e:
        raise wexc.NotFound("No such variable: %s" % e) from e

@get_vars.route('/<var>')
def get_var(vtype, job, var):
    try:
        with db.transact() as conn:
            vars = _get_vars(db.get_state(conn), vtype, job)
            return jsonify(vars[var])
    except KeyError as e:
        raise wexc.NotFound from e

@set_vars.route('/', methods=['PUT'])
def set_all_vars():
    req = request.get_json()
    if not isinstance(req, dict):
        raise wexc.UnsupportedMediaType("Not a JSON object")
    with db.transact("set_all_vars") as conn:
        vars = _get_vars(db.get_state(conn))
        vars.clear()
        vars.update(req)
        return util.empty_response

@set_vars.route('/<var>', methods=['PUT', 'DELETE'])
def set_var(var):
    meth = request.method
    try:
        with db.transact("set_var") as conn:
            vars = _get_vars(db.get_state(conn))
            if meth == 'DELETE':
                del vars[var]
            else:
                val = request.get_json()
                if val is None:
                    raise wexc.UnsupportedMediaType("Not JSON data")
                vars[var] = val
            return util.empty_response
    except KeyError as e:
        raise wexc.NotFound from e
