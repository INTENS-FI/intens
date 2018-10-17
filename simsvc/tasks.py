"""Task management (Dask client)
"""

from concurrent.futures import CancelledError
import sys, traceback as tb

import flask
from werkzeug.utils import cached_property
from dask.distributed import Client, Variable, fire_and_forget

import db

from model import task

class TaskFlask(db.DBFlask):
    """A Flask app with Dask background jobs.
    """
    def __init__(s, *args, **kws):
        """args and kws are passed to super.
        """
        super().__init__(*args, **kws)
        s.tasks = {}

    @cached_property
    def client(s):
        """Our Dask client
        """
        return Client()

    def refresh_jobs(s):
        """Check if any scheduled jobs have started.  If so, record in the
        database.  This creates and commits its own transaction.
        """
        #TODO
        pass

    def task_done(s, jid, fut):
        """Callback when a job is done.
        jid is a job id, fut is its future.
        This removes the job from tasks, updates its status and stores results
        in the database.
        """
        assert s.tasks[jid][0] == fut
        assert fut.done()
        del s.tasks[jid]
        with s.transact(note="task_done") as conn:
            job = db.get_state(conn).jobs[jid]
            try:
                job.results = fut.result()
            except CancelledError:
                job.status = db.Job_status.CANCELLED
            except:
                job.status = db.Job_status.FAILED
                job.error = "".join(tb.format_exception(*sys.exc_info()))
            else:
                job.status = db.Job_status.DONE

    def launch(s, jid, job):
        """Launch a task.
        jid is a job id, job is a db.Job.  This modifies job.
        Caller should provide a transaction and commit if launch returns.
        Otherwise we may have a running job that is not in the database.
        """
        canc = Variable()
        canc.set(False)
        fut = s.client.compute(task(job.inputs, canc))
        s.tasks[jid] = fut, canc
        job.status = db.Job_status.SCHEDULED
        fut.add_done_callback(lambda f: s.task_done(jid, f))
        fire_and_forget(fut)

    def cancel(s, jid, delete=False):
        """Attempt to cancel a task.

        jid is a job id.  If a corresponding task exists, cancel it and
        return true.  Otherwise return false.  Optionally arrange for
        the job to be deleted from the database after the task terminates.
        """
        ent = s.tasks.get(jid)
        if ent is None:
            return False
        fut, canc = ent
        if delete:
            def del_on_cancel(fut):
                if fut.cancelled():
                    with s.transact(note="del_on_cancel") as conn:
                        jobs = db.get_state(conn).jobs
                        if jobs[jid].close():
                            del jobs[jid]
            fut.add_done_callback(del_on_cancel)
        canc.set(True)
        fut.cancel()
        return True

def refresh_jobs():
    """Run TaskFlask.refresh_jobs on current app.
    """
    return flask.current_app.refresh_jobs()

def launch(jid, job):
    """Run TaskFlask.launch on current app.
    """
    return flask.current_app.launch(jid, job)

def cancel(jid, delete=False):
    """Run TaskFlask.cancel on current app.
    """
    return flask.current_app.cancel(jid, delete)
