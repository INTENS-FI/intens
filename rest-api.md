Title: Intens simulation REST API
Author: Timo Korvola
Comment: This is a Multimarkdown document.

# Intens simulation REST API

## HTTP requests

### `default/`

- GET returns list of defined defaults (names only, maybe
  `?values=true` to return also values).
- PUT with an object replaces all defaults.

#### `default/`*x*

- PUT, GET, DELETE
- Default value for input *x*

### `jobs/`

- GET returns list of defined jobs (names only, `?status=true` to
  return also statuses).
- POST defines a new job, returns `201 Created` with `Location` header
  and *id* in body.  Request content is input values.
- DELETE deletes all jobs.

#### `jobs/`*id*

- GET returns status
- DELETE cancels and removes all persistent resources.

##### `jobs/`*id*`/inputs/`

- Access to input values.  Works like `default/` but read only.  Two
  possibilities:
    1. the defaults are copied here when job is created, or
    2. it is not permitted to modify defaults while jobs exist.

##### `jobs/`*id*`/error`

- Error details of failed simulations.  Only available if status is
  failed.

##### `jobs/`*id*`/results/`

- Access to simulation results.  Works like `default/` but read only.
- Only available if status is done.
- Accessing results before simulation finishes either returns 404 (or
  maybe 409 Conflict or 503 Service unavailable) or waits.
- Accessing results of failed computations returns 404 or maybe 410 Gone.

##### `jobs/`*id*`/log`

- Stdout & stderr of the simulation app.  GET only.  text/plain.

##### `jobs/`*id*`/files`

- Working dir of job for debugging.  TBD.  May also redirect.

## Types & such

- Client & simulator back end are expected to agree on the names and
  types of inputs and outputs.  Communicating that info is not part of
  this API.
- Inputs and outputs can be any JSON types.
- Time series are not directly supported but can be passed as *n* by 2
  arrays (nested).
- Job statuses:
    * scheduled: waiting to start
    * running: started, log available
    * done: succesful termination, results available
    * canceled: trying to stop it, will delete once stopped
    * failed: terminated in error, no results
    * invalid: somehow corrupt, only possible to view files or delete.

## Socket.IO API

- To be implemented after the HTTP stuff.  Poll until this is done.
- Job status changes are emitted to a Socket.IO room named after the
  job id.
