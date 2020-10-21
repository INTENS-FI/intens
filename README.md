# INTENS optimization framework repository

This repository hosts software developed for Task 2.3 (cloud-based
optimization framework) of the INTENS project.  Notable files:

- **[doc/rest-api.md](doc/rest-api.md)** documents the simulation
  service web API
- **[doc/model-api.md](doc/model-api.md)** documents the interface for the
  simulation service to access the simulation model.
- **server** contains the simulation service implemented in Python.
- **o4j_client** contains an optimization client implemented in Java.
  It is based on the [Opt4J][] framework and [code][cityopt-gh]
  developed in the [Cityopt][] project.
- **models** contains example models for the simulation service.

## The simulation service (simsvc)

The `server` directory contains a web microserver for parallel
execution of simulations.  It needs a model to run.  For testing you
can symlink (or copy if on Windows) one of the examples to
`server/model.py` or `server/model` depending if it is a module or a
package).  Other arrangements are possible: the server just imports
`task` from `model`.

See `setup.py` for library requirements.  These are for the server;
the test script `sio-test.py` also requires `socketIO-client`.

Once a model has been provided, `python3 -m simsvc` starts the service,
running it on the Eventlet WSGI server.  Other WSGI servers can be used
if they are supported by Flask-SocketIO.  The factory function for
creating the WSGI app is `create_app` in `simsvc`.  See
`simsvc.config` for options that can be set with environment
variables.

A Docker image for the service can be built by running `make` in the
`server` directory.  See the `Makefile` for parameters.  Note that the
wheel file name may need to be updated if `setup.py` is modified.  The
image does not contain a model but is intended as a base: a runnable
image can be built by adding a model, perhaps by using
`models/Dockerfile`.  In cluster deployments the same image is
intended to be used for the server, the Dask scheduler and workers.
The default command runs the server, which in the absence of specific
Dask configuration starts workers according to the number of cores
available, thus providing the whole service in a single container.

By default the server listens at `http://localhost:8080/` if executed
outside Docker.  The Docker image listens at port 8080 on all
interfaces of the container.  The default is no authentication.  HTTP
basic authentication can be enabled by providing a htpasswd file and
pointing `HTPASSWD_FILE` to it.  That should be OK for localhost on
multi-user machines but vulnerable to eavesdropping over actual
networks.  Unix domain sockets are also somewhat supported: the
runnable `simsvc` package supports them but, e.g., Java doesn't.
Production deployments should be secured behind an ingress server that
handles SSL and authentication.

## The Opt4J client

The directory `o4j_client` contains an optimisation client for the
simulation service.  It is based on a platform developed in an earlier
project ([Cityopt][]), which in turn is based on the [Opt4J][]
library.  To build you need a Java 11 JDK and Maven.  You need to
clone the [Cityopt code from Github][cityopt-gh], as it is not
available on Maven central.  Build modules `sim-eval` and `opt-ga` and
install to your local Maven repository.  Then build `o4j_client` with
Maven.  This creates an executable jar (in `target`) with the full
Opt4J and all dependencies included.  Running it with `java -jar`
starts up the Opt4J configuration GUI.

To configure Opt4J for simsvc based optimisation select Problem/Simsvc
in the GUI.  You will need to specify modelFile, which is in YAML and
minimally needs to provide the server URL (under the key `url`).  See
class `IntensModel` for other fields, which are optional.  The
optimisation problem is specified with a CSV file (problemFile), see
[Cityopt documentation][cityopt-csv] for the format.  Time series are
not currently supported.  Owing to a Guice bug you need to specify a
valid timestamp as timeOrigin even if you don't otherwise use
timestamps (if you do use them as simulation inputs, they are passed
to simsvc as seconds since timeOrigin).  simulator should be left
empty.

To solve an optimization problem with Opt4J you also need to configure
an Optimizer, e.g., EvolutionaryAlgorithm, and some Output modules.
You should also configure Default/IndividualCompleter to run in
parallel with as many threads as your simsvc can handle (the total
number of worker cores).

[Opt4J]: http://opt4j.sourceforge.net/
[cityopt-gh]: https://github.com/Cityopt/cityopt "Cityopt on Github"
[Cityopt]: http://www.cityopt.eu/
[cityopt-csv]: https://github.com/Cityopt/cityopt/blob/master/misc/csv-formats.md
