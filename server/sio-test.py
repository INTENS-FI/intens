#!/usr/bin/python3

import logging

from socketIO_client import SocketIO

logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
logging.basicConfig()

def on_launched(jid):
    print("Launched", jid)

def on_terminated(jid):
    print("Terminated", jid)

with SocketIO("localhost", 8080) as sioc:
    sioc.on('launched', on_launched)
    sioc.on('terminated', on_terminated)
    sioc.wait()
