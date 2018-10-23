Title: Intens simulation model API
Author: Timo Korvola
Comment: This is a Multimarkdown document.

# Intens simulation model API

The simulation model is provided as a Python function
`model.task(spec, cancel)`, where `spec` is an instance of
`simsvc.tasks.Task_spec` and `cancel` is a
`dask.distributed.Variable`.  The first parameter `spec` has the
following attributes:

`inputs`
:	A mapping of input parameter names to values

`workdir`
:	The absolute name of the task work directory.

`jobid`
:   The id of the job in the database.  Tasks may use this for
    debugging purposes, e.g., in error messages, although this is not
    required.

Future extensions may introduce more attributes.  The `model.task`
function must return a Dask delayed computation, which returns the
simulation results as a mapping.  Here "mapping" is either a dict or
something with a similar interface.

The computation should regularly poll the `cancel` variable: if it
becomes true the computation should cancel itself by raising
`concurrent.futures.CancelledError`.  The directory `workdir` is
shared between the computation and the server: the computation may
create arbitrary files and subdirectories there, which can be
immediately downloaded from the server (even while the task is
running).  `workdir` is retained until the job is deleted.  Tasks may
only create files in `workdir` or temporary files managed with
`tempfile` or equivalent in the usual location for the operating
system (`dir=None` for `tempfile`) .  The latter may be faster but
the files are then inaccessible outside the task.

We may standardise some of the contents of `workdir` later, e.g.,
define names of log files.  Some such content may also be specified as
created by the server before task execution.  Currently `workdir`
starts as empty.

It is possible for `task` to create subtasks, either by returning a
non-trivial task graph or by [submitting tasks at run-time][runtime
tasks] (the latter is currently an experimental feature of Dask).  Any
subtasks that take non-negligible time should then poll `cancel`
(which must be passed to them) and cancel themselves if it becomes
true.  Cancellation propagates to waiting tasks: a task does not have
to poll `cancel` while waiting for a task that polls it.

Errors are indicated by raising exceptions.  An exception from
`model.task` causes job posting to fail, thus no job is created on the
server.  An exception from the delayed computation causes the server
to mark the job as failed.

The `model.task` function is executed on the server.  How Dask
executes the delayed computation that it returns depends on
deployment.  In a typical distributed setup each worker process can
run multiple tasks in threads.  Hence tasks must not manipulate per
process state such as the current working directory.  If a task
creates a subprocess, e.g., for running an external simulator, it may
of course manipulate the state of that subprocess.

[runtime tasks]: https://distributed.readthedocs.io/en/latest/task-launch.html
