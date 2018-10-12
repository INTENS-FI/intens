#!/usr/bin/python3

from flask import Flask, request, jsonify
import logging, dask
import db


app = db.DBFlask(__name__)
client = None

if __name__ == '__main__':
    from dask.distributed import Client
    from eventlet import wsgi, listen
    import vars
    client = Client()
    app.register_blueprint(vars.get_vars, url_prefix="/default")
    app.register_blueprint(vars.set_vars, url_prefix="/default")
    wsgi.server(listen(('', 8080)), app)
