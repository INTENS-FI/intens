# FMI support for Simsvc

This directory contains an adapter between the Simsvc model interface and
the Functional Mockup Interface.  The `*.py` files should be installed as
package `model`.  The included Dockerfile does this; create a base image with
`docker build -t simsvc-fmi .` and build model images on top of it.
 
The default result processor `util.serialise_results` does not work too
well because ZODB struggles to store all the data from larger
simulations.  Model images should add `model/custom.py` containing
`process_results` that extracts only a moderate amount of data to be stored.

A timeout can be set to kill simulations taking too long (in case the FMU
is prone to hanging with some inputs).  If a timeout is used or the worker
has multiple threads, simulations are executed in subprocesses.  This requires
the worker process not to be a daemon.  Set `distributed.worker.daemon` to
false in Dask configuration.
