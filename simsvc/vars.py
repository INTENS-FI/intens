"""Access to inputs and results.
"""

from flask import Blueprint, jsonify, request
import werkzeug.exceptions as wexc
import db
from http import HTTPStatus

get_vars = Blueprint('get_vars', __name__)
set_vars = Blueprint('set_vars', __name__)

empty_resp = ("", HTTPStatus.NO_CONTENT)

@get_vars.route('')
def get_all_vars():
    with db.db.transaction() as conn:
        st = db.get_state(conn)
        vars = st.default
        return jsonify(dict(vars))

@get_vars.route('/<var>')
def get_var(var):
    try:
        with db.db.transaction() as conn:
            st = db.get_state(conn)
            vars = st.default
            return jsonify(vars[var])
    except KeyError as e:
        raise wexc.NotFound() from e

@set_vars.route('', methods=['PUT'])
def set_all_vars():
    req = request.get_json()
    if not isinstance(req, dict):
        raise wexc.UnsupportedMediaType("Not a JSON object")
    with db.db.transaction() as conn:
        st = db.get_state(conn)
        vars = st.default
        vars.clear()
        vars.update(req)
        return empty_resp

@set_vars.route('/<var>', methods=['PUT', 'DELETE'])
def set_var(var):
    meth = request.method
    try:
        with db.db.transaction() as conn:
            st = db.get_state(conn)
            vars = st.default
            if meth == 'DELETE':
                del vars[var]
            else:
                val = request.get_json()
                if val is None:
                    raise wexc.UnsupportedMediaType("Not JSON data")
                vars[var] = val
            return empty_resp
    except KeyError as e:
        raise wexc.NotFound() from e
