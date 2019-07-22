"""HTTP basic authentication support.
"""

from flask import current_app
from flask_httpauth import HTTPBasicAuth
from passlib.apache import HtpasswdFile

ext_name = 'simsvc_auth'

auth = HTTPBasicAuth()

@auth.login_required
def require_auth():
    return

class Auth(object):
    """A Flask extension that wraps flask_httpauth.HTTPBasicAuth.

    Config value HTPASSWD_FILE is the name of the htpasswd file to
    use.  If not provided or false, authentication is disabled
    (init_app does nothing).  Otherwise HTTP basic authentication
    is required for every request.
    """
    def __init__(s, app=None):
        s.app = app
        s.htpasswd = None
        if app is not None:
            s.init_app(app)

    def init_app(s, app):
        fname = app.config.get('HTPASSWD_FILE')
        if fname:
            if not hasattr(app, 'extensions'):
                app.extensions = {}
            app.extensions[ext_name] = HtpasswdFile(fname)
            app.before_request(require_auth)

@auth.verify_password
def verify_password(user, pw):
    htpw = current_app.extensions[ext_name]
    htpw.load_if_changed()
    return htpw.check_password(user, pw) is True
