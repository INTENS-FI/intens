Title: INTENS optimization framework repository
Author: Timo Korvola
Comment: This is a Multimarkdown document.

# INTENS optimization framework repository

This repository hosts software developed for Task 2.3 (cloud-based
optimization framework) of the INTENS project.  Notable files:

- **[rest-api.md](rest-api.html)** documents the simulation service web API
- **[model-api.md](model-api.html)** documents the interface for the
  simulation service to access the simulation model.
- **server** contains the simulation service implemented in Python.
- **o4j_client** contains an optimization client implemented in Java.
  It is based on the [Opt4J][] framework and [code][cityopt-gh]
  developed in the [Cityopt project][].
- **models** contains example models for the simulation service.

## The simulation service (simsvc)

The `server` directory contains a web microserver for parallel
execution of simulations.  It needs a model to run.  For testing you
can symlink (or copy if on Windows) one of the example to
`server/model.py` or `server/model` depending if it is a module or a
package).  Other arrangements are possible: the server just imports
`task` from `model`.

See `setup.py` for library requirements.  These are for the server;
the test script `sio-client.py` also requires `socketIO-client`.

Once a model has been provided, `run-server.py` starts the service,
running it on the Eventlet WSGI server.  Other WSGI servers can be used
if they are supported by Flask-SocketIO.  The factory function for
creating the WSGI app is `create_app` in `simsvc`.  See
`simsvc.config` for options that can be set with environment
variables.

By default the server listens at `http://localhost:8080/`.  There is no
authentication or any other attempt at security, so do not change it
to listen actual network interfaces unless you are very well
firewalled.  On a multi-user machine you may want to use a Unix domain
socket instead, although that limits your server and client options.
`run-server.py` supports Unix domain sockets but, e.g., Java doesn't.
Production deployments should be secured behind an ingress server,
which handles SSL and authentication.

## The Opt4J client

The directory `o4j_client` contains an optimisation client for the
simulation service.  It is based on a platform developed in an earlier
project (Cityopt), which in turn is based on the [Opt4J][] library.
To build you need a Java 11 JDK and Maven.  You need to clone the
[Cityopt code from Github][cityopt-gh], as it is not available on
Maven central.  Build modules `sim-eval` and `opt-ga` and install to
your local Maven repository.  Then build `o4j_client` with Maven.
This creates an executable jar (in `target`) with the full Opt4J and
all dependencies included.  Running it with `java -jar` starts up the
Opt4J configuration GUI.

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
[Cityopt project]: http://www.cityopt.eu/
[cityopt-csv]: https://github.com/Cityopt/cityopt/blob/master/misc/csv-formats.md
