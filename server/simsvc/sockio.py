"""Support for simulation monitoring with Socket.IO

To use this, bind socketio to your Flask app with
socketio.init_app(app).  Unfortunately flask_socketio does not have
blueprints, which limits us to a single SocketIO instance (module
variable) and thus a single Flask app.  Then configure the app to use
Monitor as its launch monitor.  Run the app with socketio.run(app) or
see the Flask-SocketIO docs for other server options.
"""

from flask import current_app, request
from flask_socketio import SocketIO, disconnect

socketio = SocketIO()

def logger(app=None):
    if app is None:
        app = current_app
    return app.logger.getChild("sockio")

@socketio.on('connect')
def handle_connect(sid, env):
    addr = request.remote_addr
    if addr is None:
        logger().error(
            "Socket.IO: refusing connection from unknown address")
        return False
    else:
        logger().info("Socket.IO: %s connected", addr)

@socketio.on('disconnect')
def handle_disconnect(sid):
    logger().info("Socket.IO: %s disconnected", request.remote_addr)

class Monitor(object):
    """A monitor that sends events over Socket.IO.
    Instance attributes, also constructor arguments:
    app		Flask app that we monitor
    sio		SocketIO instance to use
    """
    def __init__(s, app, sio=socketio):
        s.app = app
        s.sio = sio
    
    def __call__(s, jid, fut):
        fut.add_done_callback(lambda fut: s.finish(jid, fut))
        s.sio.emit('launched', jid)

    def finish(s, jid, fut):
        s.sio.emit('terminated', jid)
