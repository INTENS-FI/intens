"""Database objects and support.
"""

from enum import Enum
import shutil

import flask
from werkzeug.utils import cached_property
from persistent import Persistent
from BTrees.OOBTree import OOBTree, difference
from BTrees.IOBTree import IOBTree
import ZODB, zodburi

class DBFlask(flask.Flask):
    """A Flask app with a database association.
    """
    @cached_property
    def db(s):
        """ZODB connection pool.
        """
        import atexit
        zuri = s.config.get('JOB_DB')
        if zuri is None:
            z = ZODB.DB("simsvc.fs")
        else:
            sf, kws = zodburi.resolve_uri(zuri)
            z = ZODB.DB(sf(), **kws)
        atexit.register(z.close)
        return z

    def transact(s, note=None):
        """Return a context manager encapsulating a transaction.

        Currently this is a thin wrapper around ZODB.DB.transaction.
        In particular:
        - exiting the with block normally commits, exceptions abort.
        - the return value of __enter__ (bound using "with transact() as
          conn") is a database connection that can be passed to functions
          of this module.
        - note is an optional transaction note, saved by ZODB.
        """
        return s.db.transaction(note)

def transact(note=None):
    """Run DBFlask.transact on current app.
    """
    return flask.current_app.transact(note)

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
    """
    INVALID = 0
    SCHEDULED = 1
    RUNNING = 2
    DONE = 3
    FAILED = -1
    CANCELLED = -2

    def active(s):
        """Scheduled or running"""
        return s in [s.SCHEDULED, s.RUNNING]

    def normal(s):
        """Scheduled, running or done"""
        return s.value > 0

class Job(Persistent):
    """Persistent data for a single job.  Instance attributes:
    status	Job_status
    inputs	A mapping (name -> value) of inputs.  Includes
    		default values as applied.
    results	A mapping (name -> value) of results (generally empty
    		unless status == DONE).
    error	An error message (str) or None.
    workdir	The working directory of the job (absolute file name)
    		or None.

    Input and result values can be of any (serializable) type.  If they
    are mutable, do not modify them or you'll confuse persistence
    management.  Replacement with a new value is fine as OOBTree handles
    persistence then.

    workdir starts as None but a working directory may be created by
    assigning the result of tempfile.mkdtemp to workdir.  The close
    method recursively removes workdir unless it is None.
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
        s.error = s.workdir = None

    def save_results(s, results):
        """Save results into the database.
        Previous results are replaced.  results is a sequence
        of (name, value) pairs or an object with a method 'items'
        that returns such a sequence (e.g., dict).  Transaction management
        is up to the caller.
        """
        s.results.clear()
        s.results.update(results)

    def close(s):
        """Remove any non-database resources associated with this job.
        On success return true: the job can now be deleted from the database
        without resource leaks.  On failure change the job status to invalid,
        set error to indicate reason for failure, and return false.

        This should be called from a transaction that will be committed
        whether closing succeeds or not.

        The working directory is only removed if
        shutil.rmtree.avoids_symlink_attacks.  Otherwise we leave it
        behind silently (returning True).  Finding a secure way to
        clean up is left as an exercise.  Sorry.
        """
        good = True
        def onerr(fn, path, ei):
            import traceback as tb
            nonlocal good
            if good:
                good = False
                s.status = Job_status.INVALID
                s.error = (("Error on closing job, on deleting %s:\n" % path)
                           + tb.format_exception(*ei))
            else:
                s.error += "Failed to delete %s.\n" % path
        if s.workdir is not None and shutil.rmtree.avoids_symlink_attacks:
            shutil.rmtree(s.workdir, onerror=onerr)
            if good:
                s.workdir = None
        return good

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

