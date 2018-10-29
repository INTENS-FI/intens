"""Support for simulation monitoring with Socket.IO

To use this, bind socketio to your Flask app with
socketio.init_app(app).  Unfortunately flask_socketio does not have
blueprints, which limits us to a single SocketIO instance (module
variable) and thus a single Flask app.  Then configure the app to use
Monitor as its launch monitor.  Run the app with socketio.run(app) or
see the Flask-SocketIO docs for other server options.
"""

from flask import current_app, request
from flask_socketio import Namespace

def logger(app=None):
    if app is None:
        app = current_app
    return app.logger.getChild("sockio")

class Simsvc_namespace(Namespace):
    def on_connect():
        addr = request.remote_addr
        if addr is None:
            logger().error(
                "Socket.IO: refusing connection from unknown address")
            return False
        else:
            logger().info("Socket.IO: %s connected", addr)

    def on_disconnect():
        logger().info("Socket.IO: %s disconnected", request.remote_addr)

class Monitor(object):
    """A monitor that sends events over Socket.IO.
    Instance attributes, also constructor arguments:
    app		Flask app that we monitor
    sio		SocketIO instance to use
    """
    def __init__(s, app, sio):
        s.app = app
        s.sio = sio
        if s.sio.async_mode == 'threading':
            s._queue = None
        elif s.sio.async_mode == 'eventlet':
            from queue import Queue
            s._queue = Queue()
            def emitter():
                from eventlet import tpool
                while True:
                    ev, arg = tpool.execute(s._queue.get)
                    s.sio.emit(ev, arg)
            s.sio.start_background_task(emitter)
        else:
            raise ValueError("Unsupported socketio.asyncmode %s"
                             % s.sio.async_mode)

    def __call__(s, jid, fut):
        fut.add_done_callback(lambda fut: s.finish(jid, fut))
        s.sio.emit('launched', jid)
    
    def _emit(s, ev, arg):
        if s._queue is None:
            s.sio.emit(ev, arg)
        else:
            s._queue.put((ev, arg))

    def finish(s, jid, fut):
        s._emit('terminated', jid)
