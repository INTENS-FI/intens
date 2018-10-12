"""Database objects and support.
"""

from enum import Enum
import flask
from werkzeug.utils import cached_property
from persistent import Persistent
from BTrees.OOBTree import OOBTree, difference
from BTrees.IOBTree import IOBTree
import ZODB

class DBFlask(flask.Flask):
    """A Flask app with a database association.
    """
    @cached_property
    def db(s):
        """ZODB connection pool.
        """
        import atexit
        #TODO config
        z = ZODB.DB("app.fs")
        atexit.register(z.close)
        return z

def transact(note=None):
    """Return a context manager encapsulating a transaction.

    The database connection is obtained from flask.current_app, which must be
    available and an instance of DBFlask.  Currently this is a thin wrapper
    around ZODB.DB.transaction.  In particular:
    - exiting the with block normally commits, exceptions abort.
    - the return value of __enter__ (bound using "with transact() as conn")
      is a database connection that can be passed to functions of this module.
    - note is an optional transaction note, saved by ZODB.
    """
    return flask.current_app.db.transaction(note)

class App_state(Persistent):
    """Application state.
    Contains everything that we store in the database.  Instance attributes:
    default	a mapping of default inputs (name -> value)
    jobs	a mapping of Jobs (job id -> Job)
    """
    def __init__(s):
        s.default = OOBTree()
        s.jobs = IOBTree()

def get_state(conn):
    """Return the application state.
    If it does not exist, create it.
    conn is a database connection.
    """
    r = conn.root
    try:
        return r.app_state
    except AttributeError:
        st = r.app_state = App_state()
        return st

class Job_status(Enum):
    """Job states.
    Positive values are normal, others exceptional. 
    """
    INVALID = 0
    SCHEDULED = 1
    RUNNING = 2
    DONE = 3
    FAILED = -1
    CANCELED = -2


class Job(Persistent):
    """Persistent data for a single job.  Instance attributes:
    status	Job_status
    inputs	A mapping (name -> value) of inputs.  Includes
    		default values as applied.
    results	A mapping (name -> value) of results (generally empty
    		unless status == DONE).
    error	An error message (str) or None.

    Input and result values can be of any (serializable) type.  If they
    are mutable, do not modify them or you'll confuse persistence
    management.  Replacement with a new value is fine as OOBTree handles
    persistence then.
    """
        
    def __init__(s, inputs, defaults):
        """Initialise from given inputs and defaults, which are name -> value
        collections.  The job inputs are their union, with values in
        inputs having precedence over defaults.
        """
        s.status = Job_status.INVALID
        s.inputs = OOBTree()
        s.inputs.update(inputs)
        s.inputs.update(difference(defaults, s.inputs))
        s.results = OOBTree()
        s.error = None

def gen_jobid(jobs):
    if not jobs:
        return 1
    mk = jobs.maxKey()
    if mk > 10 * len(jobs):
        return randrange(1, mk)
    else:
        return mk + 1

def create_job(conn, inputs):
    """Create a Job and add to the job list.
    Return (job id, Job).
    """
    st = get_state(conn)
    j = Job(inputs, st.default)
    k = gen_jobid(st.jobs)
    while not st.jobs.insert(k, j):
        k = gen_jobid(st.jobs)
    return k, j

