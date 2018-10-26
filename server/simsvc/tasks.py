"""Task management (Dask client)
"""

from concurrent.futures import CancelledError
import queue, sys, traceback as tb

import flask
from werkzeug.utils import cached_property
from dask.distributed import Client, Variable, fire_and_forget

from . import db

from model import task

class Task_spec(object):
    """Parameters passed to a simulation task.
    The task should treate this as read-only.

    Instance attributes:
    inputs	A dict-like of input parameter names and values
    workdir	The name of the task working directory.  Any files that
		the task creates here are immediately downloadable
    		from the server.
    jobid	The job id.  Possibly useful for log messages.
    """
    def __init__(s, jobid, job):
        """Initialize from a .db.Job"""
        s.inputs = job.inputs
        s.workdir = job.workdir
        s.jobid = jobid

class TaskFlask(db.DBFlask):
    """A Flask app with Dask background jobs.

    Instance attributes:
    tasks	Active tasks.  job id -> (future, cancellation flag).
    		Entries are added by launch and deleted by callback when
    		futures terminate - which can happen at any time.  If
		you need to iterate over tasks, make a copy.
    updates	A queue of scheduled database updates.  Because future
    		callbacks may execute at any time from any thread in
    		the process, it is unsafe to modify the database
    		from them.  Modifications are queued here instead.
    		Entries are functions taking a database connection as argument.
    		They are executed by flush_updates.
    monitor	An optional launch monitor.  Unless None
    		monitor(job id, future) is called after a new job is launched.
    		The monitor may call future.add_done_callback to detect
    		job termination.  Exceptions raised by monitor are logged
    		and suppressed.
    """
    def __init__(s, *args, **kws):
        """args and kws are passed to super.
        """
        super().__init__(*args, **kws)
        s.tasks = {}
        s.updates = queue.Queue()
        s.monitor = None

    @cached_property
    def client(s):
        """Our Dask client
        """
        return Client()

    def flush_updates(s, conn=None):
        """Perform any scheduled database updates.

        A database connection may be provided; if not, creates and
        commits its own transaction.  In either case, updates are bundled
        into the same transaction.  If any update raises an exception,
        it is logged and suppressed.  There is no provision for
        retrying; also failed updates are removed from the queue.  It
        is also possible that commit will fail.

        Should be called before any request involving jobs.

        Joining s.updates is deprecated and not very useful: it waits
        for all update functions to be called and return but not for
        their transaction to be committed.  We may switch to
        SimpleQueue at some point.
        """
        if conn is None:
            with s.transact("flush_updates") as conn:
                return s.flush_updates(conn)
        while True:
            try:
                upd = s.updates.get_nowait()
                upd(conn)
            except queue.Empty:
                break
            except:
                s.logger.exception("Scheduled update failed.")
            s.updates.task_done()

    def refresh_jobs(s, conn=None):
        """Check if any scheduled jobs have started.  If so, record in the
        database.  A database connection may be provided; if not,
        creates and commits its own transaction.

        Should be called before any request that needs to distinguish
        between scheduled and running jobs.
        """
        if conn is None:
            with s.transact("refresh_jobs") as conn:
                return s.refresh_jobs(conn)
        jobs = db.get_state(conn).jobs
        for jid, (fut, canc) in list(s.tasks.items()):
            job = jobs.get(jid)
            if job is None:
                s.logger.error("Cancelling unknown task %s.", jid)
                s.cancel(jid)
            elif not job.status.active():
                s.logger.error("Cancelling task %s with invalid status %s",
                               jid, job.status.name)
                job.status = db.Job_status.INVALID
                s.cancel(jid)
            # This does not work because Dask futures don't implement running.
            # elif fut.running() and job.status == db.Job_status.SCHEDULED:
            #     job.status = db.Job_status.RUNNING

    def task_done(s, jid, fut):
        """Callback when a job is done.
        jid is a job id, fut is its future.
        Remove the job from tasks and schedule a database update for saving
        results.
        """
        assert s.tasks[jid][0] == fut
        assert fut.done()
        del s.tasks[jid]
        def save_job(conn):
            job = db.get_state(conn).jobs[jid]
            try:
                job.save_results(fut.result())
            except CancelledError:
                s.logger.debug("Job %s cancelled", jid)
                # We sometimes cancel invalid tasks.
                if job.status != db.Job_status.INVALID:
                    job.status = db.Job_status.CANCELLED
            except:
                s.logger.debug("Job %s failed", jid)
                job.status = db.Job_status.FAILED
                job.error = "".join(tb.format_exception(*sys.exc_info()))
            else:
                s.logger.debug("Job %s done", jid)
                job.status = db.Job_status.DONE
        s.updates.put(save_job)

    def launch(s, jid, job):
        """Launch a task.
        jid is a job id, job is a db.Job.  This modifies job.
        Caller should provide a transaction and commit if launch returns.
        Otherwise we may have a running job that is not in the database.
        """
        canc = Variable()
        canc.set(False)
        spec = Task_spec(jid, job)
        fut = s.client.compute(task(spec, canc))
        s.tasks[jid] = fut, canc
        job.status = db.Job_status.SCHEDULED
        fut.add_done_callback(lambda f: s.task_done(jid, f))
        fire_and_forget(fut)
        if s.monitor is not None:
            try:
                s.monitor.launch(jid, fut)
            except:
                s.logger.exception("monitor.launch failed for job %s", jid)

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
                def del_job(conn):
                    s.logger.debug("Deleting job %s on cancel", jid)
                    jobs = db.get_state(conn).jobs
                    if jobs[jid].close():
                        del jobs[jid]
                if fut.cancelled():
                    s.updates.put(del_job)
            fut.add_done_callback(del_on_cancel)
        canc.set(True)
        fut.cancel()
        return True

    def cancel_all(s, delete=False):
        """Cancel all active tasks.

        Return a list of job ids that were cancelled.  Optionally arrange
        for each job to be deleted from the database after its task
        terminates.
        """
        canc = list(s.tasks)
        for jid in canc:
            s.cancel(jid, delete)
        return canc

    def sync_tasks(s):
        """Synchronise the database with run-time task state.

        Compare run-time tasks with active jobs in the database.  Call
        flush_updates, then check that each active job has a task; if
        not, launch one.  Most likely a previous app instance crashed.
        Then call refresh_jobs to ensure that all tasks have an active job.
        Everything is done in a single transaction created here.  When
        launching tasks exceptions are logged and suppressed.

        This should be called at startup and periodically.  Calling it
        at every request may be a bit expensive.  flush_updates and
        refresh_jobs should be sufficient for that and faster.
        """
        snap = frozenset(s.tasks)
        with s.transact("sync_tasks") as conn:
            s.flush_updates(conn)
            jobs = db.get_state(conn).jobs
            for jid, job in jobs.items():
                if job.status.active() and jid not in snap:
                    try:
                        s.launch(jid, job)
                    except:
                        s.logger.exception("Failed to relaunch job %s", jid)
                    else:
                        s.logger.info("Relaunched job %s", jid)
            s.refresh_jobs(conn)

def flush_updates():
    """Run TaskFlask.flush_updates on current app.
    """
    return flask.current_app.flush_updates()
    
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

def cancel_all(delete=False):
    """Run TaskFlask.cancel_all on current app.
    """
    return flask.current_app.cancel_all(delete)
