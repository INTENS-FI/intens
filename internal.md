# Glossary

- In this document Python names starting with a dot are
  relative to `simsvc`.
- *Real threads* are threads provided by the Python standard library,
  implemented using OS threads.  *Green threads* are coroutines
  provided by the Eventlet or Gevent library.  The APIs of these
  libraries are designed to resemble programming with real threads.
  Real threads are usually preemptively scheduled and would execute
  concurrently were it not for the CPython global interpreter lock.
  Each real thread can host any number or green threads, which are
  cooperatively scheduled within their real thread.
- Green thread switching happens during calls to the Eventlet or
  Gevent library.  *Monkey patching* is a function provided by
  these libraries that modifies the Python standard library to
  support green threads: green thread switching will then also occur
  while waiting for I/O in a monkey patched standard library routine.
- *Jobs* are entries in the database of class `.db.Job`.  Each has
  inputs, results and a status.  Jobs are identified by
  server-generated ids.  A client creates a job by posting its
  inputs.  The job persists in the database until it is deleted.  Its
  properties change as the job is executed and can be queried but
  not changed by clients.
- *Tasks* are run-time state for jobs.  Currently a task is a (future,
  variable) pair of `dask.distributed` objects.[^taskextend] The
  variable is used for cancellation requests.  A task is generated
  when a job is scheduled.  When the task terminates its results are
  stored in the database and the task is deleted.  A job is *active* if
  it has a task.
- The *model* is a Python function with a fixed calling convention.
  Currently it is always named `model.task` but that may become
  configurable later.
- Each job has a *work directory*, which is created when the job is
  posted and persists as the job does.  The work directory is on a
  file system shared among the workers and the server, which serves
  its contents to clients (read only).  The name of the work directory
  is passed to the model.  Note that the model must not actually
  change the working directory of the Dask worker because the same
  worker may execute multiple tasks concurrently in threads.  Usually
  the model launches a subprocess for running an external simulator;
  the working directory of the subprocess can and usually should be
  set to the task work directory.
- Models typically have inputs that are fixed for the current
  optimization problem, i.e., not dependent on decision variables.  In
  fact there are often more fixed than varying inputs.  To avoid
  clients having to post the fixed inputs with every job the server
  maintains a set of *default values*.  The actual job inputs are the
  union of the defaults and the posted job-specific values, with the
  latter taking precedence.  The union is computed when the job is
  posted and stored as the job inputs.  The defaults can be changed at
  any time, thus it is important to store the full actual inputs with
  the job.

[^taskextend]: If we need more state later, we'll likely define a
    class rather than extend the tuple.

# Concurrency

## I/O

- Turns out that with Eventlet Socket.IO only works from the server
  real thread (any green thread therein will do).  Dask future
  callbacks execute in dedicated real threads, one per future.  Don't
  know if monkey patching would turn those green.  We don't do that
  though, so we now have a queue (in `.sockio.Monitor`) where future
  callbacks post events for a background coroutine to emit.
- To avoid having lots of small concurrent transactions, job results
  are not saved by the task callback.  Saving is queued by the
  callback for later execution by `.tasks.flush_updates`.  Deletion
  of active jobs uses the same queue (a callback queues the deletion
  when the task finishes).

## ZODB

Currently we use Eventlet without monkey patching, thus requests
execute sequentially, or at least their database I/O does (HTTP I/O
happens in the Eventlet server code, thus hopefully with proper use of
green threads).  That would be inefficient if we had lots of clients,
but we only expect to serve one.  This section is mostly about what
would go wrong if we had more concurrency from either monkey patching
or using a real threaded server.

- Jobs are launched immediately after posting, in a single
  transaction.  If the task fails to launch, the transaction is
  aborted.  Because only the created new job is modified, there should
  be no transaction conflicts.  We currently don't handle them; if
  commit fails, we have a runaway task without a job in the database
  `.tasks.TaskFlask.refresh_jobs` should cancel it but it may take a
  while to get called.  The work directory will leak.
- Periodic coroutines flush updates and pack the database when using
  Eventlet.  If we want to monkey patch or do periodic maintenance in
  a threaded server, we need some kind of locking that prevents 
  periodic maintenance from being interleaved with request transactions.
- Concurrent default value modifications may well conflict.  No harm
  in throwing that at the client.
- Get requests on jobs call `.tasks.refresh_jobs`.  It should update
  job status from scheduled to running but currently does not, because
  there appears no way to detect the change.  If it did that, it could
  conflict with job cancellation.  `refresh_jobs` also kills runaway tasks
  and may mark jobs invalid if they had a task when they should not.
  That could also conflict with cancellation.
- If `.tasks.flush_updates` is executed concurrently with itself,
  updates may get flushed in different transactions.  There should be
  at most one update and one deletion pending for a job.  I would
  expect those not to conflict.
- Deletion of inactive jobs should not conflict with modifications.
- Deletion of an active job first cancels it.
- Cancellation immediately sets job status to cancelled, which
  may conflict if the job happens to finish normally at the same time.
  That should be resolved for normal termination.
