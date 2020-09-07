"""Task management (Dask client)
"""

from concurrent.futures import CancelledError
import queue, sys, traceback as tb

import flask
from werkzeug.utils import cached_property
import dask.distributed as dd
import dask.config

from . import db

import model

def make_kube(pod_spec, **kws):
    """Create a dask_kubernetes.KubeCluster.

    pod_spec is either the name of a YAML file containg the worker pod
    specification or a dict containing the specification directly.
    kws is passed to KubeCluster.from_yaml or .from_dict.
    """
    from dask_kubernetes import KubeCluster
    if isistance(pod_spec, str):
        return KubeCluster.from_yaml(pod_spec, **kws)
    else:
        return KubeCluster.from_dict(pod_spec, **kws)

def make_slurm(**kws):
    """Create a dask_jobqueue.SLURMCluster.

    kws is passed to the constructor.  This is just a simple wrapper
    to avoid importing dask_jobqueue unless called.
    """
    from dask_jobqueue import SLURMCluster
    return SLURMCluster(**kws)

cluster_types = {'local': dd.LocalCluster, 'kubernetes': make_kube,
                 'slurm': make_slurm}

def timeout_kluge(f, logger=None):
    """Return f(), handle IOErrors.
    If f raises IOError with a message containing "timed out" (in any case),
    raise TimeoutError.  If logger is given, log an info message.  Other
    IOErrors are re-raised as is.  This is a workaround for dask.distributed
    raising IOError on timeout instead of TimeoutError.
    """
    try:
        return f()
    except IOError as e:
        if "timed out" in str(e).lower():
            if logger is not None:
                logger.info("Apparent timeout detected.")
            raise dd.TimeoutError("Apparent timeout") from e
        else:
            raise

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

#XXX Can this actually be made to work somehow?
class Bogo_var(object):
    """Pretends to be a dask.distributed.Variable but is not actually shared.
    """
    def __init__(s):
        s.value = None

    def get(s):
        return s.value

    def set(s, v):
        s.value = v

class TaskFlask(db.DBFlask):
    """A Flask app with Dask background jobs.

    Instance attributes:
    tasks	Active tasks.  job id -> (future, cancellation flag).
    		Entries are added by launch and deleted by callback when
    		futures terminate - which can happen at any time.  If
		you need to iterate over tasks, make a copy.
    gathers	Finished tasks whose results should be gathered before
		executing database updates.  job id -> future.
    updates	A queue of scheduled database updates.  Because future
    		callbacks may execute at any time from any thread in
    		the process, it is unsafe to modify the database
    		from them.  Modifications are queued here instead.
    		Entries are functions.  They are called by flush_updates
		as upd(conn, res) where conn is a database connection and
		res is a dictionary job id -> result.  Updates that need
		results should first check res and if not found there,
 		call the result method on the task future.
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
        s.gathers = {}
        s.updates = queue.Queue()
        s.monitor = None

    @cached_property
    def cluster(s):
        """Our Dask cluster or None if we were not configured to create one.
        """
        cltype = dask.config.get('simsvc.cluster.type')
        if cltype is None:
            return None
        ctor = cluster_types.get(cltype)
        if ctor is None:
            raise KeyError("Unknown cluster type %s" % cltype)
        clust = ctor(**dask.config.get('simsvc.cluster.args'))
        ad = dask.config.get('simsvc.cluster.adapt')
        if ad:
            clust.adapt(**ad)
        return clust

    @cached_property
    def client(s):
        """Our Dask client
        """
        def make_client():
            args = dask.config.get('simsvc.client-args')
            if s.cluster is None:
                return dd.Client(**args)
            else:
                return dd.Client(s.cluster, **args)
        while True:
            try:
                cli = timeout_kluge(make_client, s.logger)
                break
            except dd.TimeoutError:
                s.logger.warning("Scheduler connection timed out; retrying")
        if hasattr(model, 'worker_callback'):
            cli.register_worker_callbacks(model.worker_callback)
        return cli

    def flush_updates(s, conn=None):
        """Perform any scheduled database updates.

        A database connection may be provided; if not, creates and
        commits its own transaction.  In either case, updates are bundled
        into the same transaction.

        Updates that raise TimeoutError are re-queued after the whole
        queue has been processed.  Before raising such an update
        function must add its job back to gathers but must not add
        itself to updates (that will be done here).

        Any other exceptions from updates are logged and suppressed.
        They do not cause a retry; the failed updates are removed
        from the queue.  It is also possible that commit will fail;
        there is no provision for retrying that.

        Should be called before any request involving jobs.

        Joining s.updates is deprecated and not very useful: it waits
        for all update functions to be called and return but not for
        their transaction to be committed.  We may switch to
        SimpleQueue at some point.
        """
        if conn is None:
            with s.transact("flush_updates") as conn:
                return s.flush_updates(conn)
        gat = s.gathers
        s.gathers = {}
        if gat:
            s.logger.debug("Gathering %s futures", len(gat))
            res = s.client.gather(gat, errors='skip')
            if len(res) < len(gat):
                bad = gat.keys() - res.keys()
                s.logger.error("Errors gathering %s futures: %s",
                               len(bad), bad)
        else:
            res = {}
        s.logger.debug("Flushing approximately %s updates", s.updates.qsize())
        bad = []
        while True:
            try:
                upd = s.updates.get_nowait()
                if isinstance(upd, (list, tuple)):
                    upd[0](conn, res, *upd[1:])
                else:
                    upd(conn, res)
            except queue.Empty:
                break
            except TimeoutError:
                bad.append(upd)
            except:
                s.logger.exception("Scheduled update failed.")
            s.updates.task_done()
        for b in bad:
            s.updates.put(b)

    def refresh_jobs(s, conn=None):
        """Check if any scheduled jobs have started.  If so, record in the
        database.  A database connection may be provided; if not,
        creates and commits its own transaction.  Also check that each
        task corresponds to an active job in the database.  Cancel any
        task that does not.

        Should be called before any request that needs to distinguish
        between scheduled and running jobs.
        """
        if conn is None:
            with s.transact("refresh_jobs") as conn:
                return s.refresh_jobs(conn)
        jobs = db.get_state(conn).jobs
        for jid, (fut, canc) in list(s.tasks.items()):
            # task_done will clean this up or is doing it now.
            if fut.done():
                continue
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

        jid is a job id, fut its future.  Schedule a database
        update for saving results and remove the job from tasks.
        """
        assert s.tasks[jid][0] == fut
        assert fut.done()
        def save_job(conn, res):
            job = db.get_state(conn).jobs.get(jid)
            if job is None:
                s.logger.error("Job %s is gone.  Not saving it then.", jid)
                return
            try:
                r = res.get(jid)
                if r is None:
                    r = timeout_kluge(fut.result, s.logger)
                job.save_results(r)
            except CancelledError:
                s.logger.debug("Job %s cancelled", jid)
                # We sometimes cancel invalid tasks.
                if job.status != db.Job_status.INVALID:
                    job.status = db.Job_status.CANCELLED
            except TimeoutError:
                s.logger.error("Timeout fetching job %s, will retry", jid)
                s.gathers[jid] = fut
                raise
            except:
                s.logger.debug("Job %s failed", jid)
                job.status = db.Job_status.FAILED
                job.error = "".join(tb.format_exception(*sys.exc_info()))
            else:
                s.logger.debug("Job %s done", jid)
                job.status = db.Job_status.DONE
        s.gathers[jid] = fut
        s.updates.put(save_job)
        del s.tasks[jid]
        s.logger.debug("Task %s done", jid)

    def launch(s, jid, job):
        """Launch a task.
        jid is a job id, job is a db.Job.  This modifies job.
        Caller should provide a transaction and commit if launch returns.
        Otherwise we may have a running job that is not in the database.
        """
        canc = Bogo_var()
        canc.set(False)
        spec = Task_spec(jid, job)
        fut = s.client.compute(model.task(spec, canc))
        s.tasks[jid] = fut, canc
        job.status = db.Job_status.SCHEDULED
        fut.add_done_callback(lambda f: s.task_done(jid, f))
        dd.fire_and_forget(fut)
        if s.monitor is not None:
            try:
                s.monitor(jid, fut)
            except:
                s.logger.exception("monitor.launch failed for job %s", jid)

    def cancel(s, jid, delete=False):
        """Attempt to cancel a task.

        jid is a job id.  If a corresponding task exists and is not done,
        cancel it and return true.  Otherwise return false.  Optionally
        arrange for the job to be deleted from the database after the
        task terminates (or immediately if it had already terminated).
        """
        ent = s.tasks.get(jid)
        if ent is None:
            return False
        fut, canc = ent
        if delete:
            def del_job(conn, res):
                s.logger.debug("Deleting job %s on cancel", jid)
                jobs = db.get_state(conn).jobs
                if jobs[jid].close():
                    del jobs[jid]
            def del_on_cancel(fut):
                if fut.cancelled():
                    s.updates.put(del_job)
            fut.add_done_callback(del_on_cancel)
        if fut.done():
            return False
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
        live = set(s.tasks)
        with s.transact("sync_tasks") as conn:
            s.flush_updates(conn)
            # Don't relaunch timed out jobs.
            live |= s.gathers.keys()
            jobs = db.get_state(conn).jobs
            for jid, job in jobs.items():
                if job.status.active() and jid not in live:
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
