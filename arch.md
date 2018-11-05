# Optimizer

- Let's start with Opt4J.  Maybe later Dakota.
- Optimizer needs to execute lots of simulation runs: multiple
  generations with several runs per generation.
- Runs in the same generation can be executed in parellel,
  those in different generations cannot (each generation depends on
  the previous ones).
- The generation size is assumed known at the start.
- Each run should take roughly the same amount of time, but sometimes
  they don't.
- Optimizer itself may run in or out of the cluster.  E.g., Opt4J has
  a nice GUI, so people may want to run it locally.

# Simulation runs

- Each simulation run involves simulating a model with a simulator.
- A model consists of data files and information on how to run it,
  in particular which simulator to use.
- Simulators could and probably should be packaged as Docker images.
- Different simulators may need different operating systems.
- Models could contain the image name and a short driver script for
  executing the simulation.
- Models could also be packaged as Docker images but that may be too
  clumsy.  The other option would be some kind of distributed storage
  (S3 clone?).
- Some parameters vary between runs.  They need to be passed from the
  optimizer to the simulation run, perhaps in a small data file.
- Simulation result data must be passed back to the optimizer.
  Minimully these can be just the objective values.
- Simulation runs may fail, which must be indicated to the optimizer.
- Runs typically produce log messages and maybe other data that should
  be retained for debugging but does not need to be gathered into the
  optimizer.
- A single decision may take multiple runs to evaluate: typically
  how well it performs in different circumstances.

# Simulation server

- Optimizer talks with a simulation server over a REST API.
- Simulation server runs in cluster.
- REST microserver maybe implemented with Flask.
- Schedules jobs with Dask.
- Ideally mostly independent on Kubernetes: could run, e.g., on
  Slurm, whatever is supported by Dask.
- Current plan: one cluster app per optimization run.  Optimizer
  deploys it before starting and takes down at the end (can be
  automated but is Kubernetes specific and requires cluster admin rights).
- Constantly running ingress server on cluster manages access to all
  optimization apps.
- Larger data sets passed via the file system (when running locally)
  or S3.  Dask should be able to use either one with ease.  S3 more work
  on the client side.
- Simulation server and simulator mostly exchange data via files, as
  simulators don't know anything else.  Use a Kubernetes volume for
  that, so output from each run is retained for debugging and can be
  accessed by any pod.

# Proto design

## Client (based on Cityopt)

- On the client, a model is a YAML file.  It defines the base URL of
  the simulation server, maybe auth details, little else for now.
  The simulation server is deployed manually with the model in the
  image.
- In Cityopt SimulationManager.parseModel reads the YAML with
  Jackson.
- For now the client is assumed to know what inputs and outputs the
  model has.  Cityopt can already read that from CSV.

## Client-server API

- Jobs are posted on the server, which assigns & returns job ids.
- Need to figure out how to express the inputs, particularly time
  series.
- There are likely lots of parameter data (incl. time series) shared
  by all runs and a little that vary (depend on decision variables).
  So provide means for setting default values and only include
  non-defaults when posting a job.
- Status can be queried, results can be waited for.  Maybe use
  socket.io for the latter.

## Server

- The server image contains the Flask app, Dask, WSGI server, the
  simulator, the model and an implementation of a Python API for
  simulating the model.  For simplicity, the server, scheduler and
  workers all use the same image.
- Waitress may need to be replaced for better async (websockets).
- For cloud deployment we'll have a single ingress server (per
  cluster), which handles authentication and routes requests by base
  URL to per model instances of the simulation server.  The ingress
  server runs constantly at a known address.  Model instances come and
  go, so the ingress server must be dynamically configurable with
  Kubernetes (configmaps or something).  Maybe Nginx or Ambassador.
  Both should support websockets.
- There is a shared volume among server & workers with a directory
  per simulation run.  The server can read it, e.g., for logs even
  while the simulation is running.

# Questions

- Is there an existing API for packaging models?  FMI for
  co-simulation is not quite it: we want to let the simulator run at
  its own time step and get the whole trajectory when it's done, not
  just the final state.  Dakota is not quite it either, because time
  series inputs and outputs are not supported (the file formats are
  quite crummy).
