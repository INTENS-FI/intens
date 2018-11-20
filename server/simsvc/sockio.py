"""Support for simulation monitoring with Socket.IO

To use this, create a SocketIO instance bound to your app with
socketio = SocketIO(app) and route the default namespace with
socketio.on_namespace(Simsvc_namespace()).  Then configure the app to use
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
    """Default namespace handler for simsvc.
    """
    def on_connect(s):
        addr = request.remote_addr
        if addr is None:
            logger().error(
                "Socket.IO: refusing connection from unknown address")
            return False
        else:
            logger().info("Socket.IO: %s connected", addr)

    def on_disconnect(s):
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
        st = ('cancelled' if fut.cancelled()
              else 'failed' if fut.exception()
              else 'done')
        s._emit('terminated', {'job': jid, 'status': st})
