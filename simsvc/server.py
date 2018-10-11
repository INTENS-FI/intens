#!/usr/bin/python3

from flask import Flask, request, jsonify
import logging, dask


app = Flask(__name__)
client = None

if __name__ == '__main__':
    from db import setup_db
    from dask.distributed import Client
    from eventlet import wsgi, listen
    import vars
    setup_db(app)
    client = Client()
    app.register_blueprint(vars.get_vars, url_prefix="/default")
    app.register_blueprint(vars.set_vars, url_prefix="/default")
    wsgi.server(listen(('', 8080)), app)
