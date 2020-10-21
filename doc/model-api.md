# Intens simulation model API

## Configuration

Dask configuration for `simsvc` has been loaded by the time that the
simulation model is imported.  The key `simsvc.model` is reserved for
use by the model.

## The main entry point: model.task

The simulation model is provided as a Python function
`model.task(spec, cancel)`, where `spec` is an instance of
`simsvc.tasks.Task_spec` and `cancel` is a
`dask.distributed.Variable`.  The first parameter `spec` has the
following attributes:

`inputs`
:	A mapping of input parameter names to values

`workdir`
:	The absolute name of the task work directory or `None` if not
    available

`jobid`
:   The id of the job in the database.  Tasks may use this for
    debugging purposes, e.g., in error messages, although this is not
    required.

Future extensions may introduce more attributes.  The `model.task`
function must return a Dask delayed computation, which returns the
simulation results as a mapping.  Here "mapping" is either a dict or
something with a similar interface.

The `cancel` variable was intended as a mechanism for cancelling
tasks: computations would regularly poll it, and if it should become
true the computation would cancel itself by raising
`concurrent.futures.CancelledError`.  However, this idea had to be
abandoned because of performance problems.  Currently the `cancel`
parameter is in fact not a `dask.distributed.Variable`; it just mimics
the interface without actually being shared.  The server has no means
for interrupting computations.

The directory `workdir`, unless `None`, is shared between the
computation and the server: the computation may create arbitrary files
and subdirectories there, which can be immediately downloaded from the
server (even while the task is running).  `workdir` is retained until
the job is deleted.  Tasks may only create files in `workdir` or
temporary files managed with `tempfile` or equivalent in the usual
location for the operating system (`dir=None` for `tempfile`).  The
latter may be faster but the files are then inaccessible outside the
task.  If `workdir` is `None` only temporary files may be created.

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
server.  An exception other than `TimeoutError` or `CancelledError`
from the delayed computation causes the server to mark the job as
failed.  `TimeoutError` must not be raised by the model.  The
conditions for raising `CancelledError` are descibed above.

The `model.task` function is executed on the server.  How Dask
executes the delayed computation that it returns depends on
deployment.  In a typical distributed setup each worker process can
run multiple tasks in threads.  Hence tasks must not manipulate per
process state such as the current working directory.  If a task
creates a subprocess, e.g., for running an external simulator, it may
of course manipulate the state of that subprocess.

[runtime tasks]: https://distributed.readthedocs.io/en/latest/task-launch.html

## Hooks

If `model.worker_callback` is defined, it is registered as a worker
callback.  See `distributed.Client.register_worker_callbacks`.

## Supporting the Opt4J client

The Opt4J client stems from an earlier project and inherits its data
model.  It has a two-level namespace for inputs and outputs: they have
a component and a name.  Both are Python identifiers, in particular
cannot contain a period.  The component `CITYOPT` is reserved; its
members `simulation_start` and `simulation_end`, if present, define
the simulation period in seconds.  The simulation service has no such
hierarchy, just a flat namespace where any string can serve as a name.
The client uses names of the form `component.name` with simsvc.
Models must support such names in order to be usable with the client,
regardless of the model actually exposing a useful component
structure.  E.g., `models/fmi` treats component `p` as containing
parameters and stores all outputs in component `o`.
