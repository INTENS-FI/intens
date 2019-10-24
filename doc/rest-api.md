Title: Intens simulation REST API
Author: Timo Korvola
Comment: This is a Multimarkdown document.

# Intens simulation REST API

## HTTP requests

All URLs are relative to the environment variable `SIMSVC_ROOT` on the
server, default `/`.

### `default/`

- GET returns the names of defined defaults as a list.  With
  `?values=true` or `?only=v1,v2,...` it returns a JSON object with
  names and values.  `only` restricts output to the listed variables,
  which must all exist, otherwise `404 Not found` results.
- PUT with an object replaces all defaults.

#### `default/`*x*

- PUT, GET, DELETE
- Default value for input *x*

### `jobs/`

- GET returns the list of defined job ids.  With `?status=true`
  returns also statuses as a JSON object with ids as keys (converted
  to strings).  `?only=id1,id2,...` restricts output to the listed job
  ids.  It is not an error if some of the listed jobs do not exist:
  such ids are simply omitted from the output.
- POST defines a new job, returns `201 Created` with `Location` header
  and *id* in body.  Request content is input values.  They are merged
  with the defaults, posted values taking precedence.
- DELETE deletes all jobs.

#### `jobs/`*id*

- GET returns status
- DELETE cancels the job and removes its persistent resources.

##### `jobs/`*id*`/inputs/`

- Access to input values.  Works like `default/` but read only.

##### `jobs/`*id*`/error`

- Error details of failed simulations.  Only available if status is
  failed.  A JSON string (quoted).

##### `jobs/`*id*`/results/`

- Access to simulation results.  Works like `default/` but read only.
- Only available if status is done.
- Accessing results of unfinished computations returns 503 Service
  unavailable or waits.
- Accessing results of unsuccesful computations returns 410 Gone.

##### `jobs/`*id*`/files/`*path*

- Retrieve a file from the working directory of a job (for debugging).
  The file is sent as is.  MIME type may be guessed or something
  generic.
- It is not specified what happens if path refers to a directory (is
  empty or ends in a slash).  The server may produce a HTML directory
  listing to facilitate access with a regular web browser.
- These URLs may redirect to a location that the server associates
  with static files.  The static files may be served by a differnent
  server that is more efficient with them.

##### `jobs/`*id*`/dir/`*path*

- List the working directory of a job (if path is empty) or a
  subdirectory.  Returns a list of [name, type]
  pairs, where type is "-" for a regular file, "d" for a
  directory, "l" for a symlink and "?" for unknown.
- This API is experimental, even more so than the rest.

## Types & such

- Client & simulator back end are expected to agree on the names and
  types of inputs and outputs.  Communicating that info is not part of
  this API.
- Inputs and outputs can be any JSON types.
- Time series are not directly supported but can be passed as *n* by 2
  arrays (nested).
- Job statuses:
    * SCHEDULED: waiting to start
    * RUNNING: started (optional: the server may also report running
      jobs as SCHEDULED if it cannot distinguish between the two states)
    * DONE: succesful termination, results available
    * CANCELLED: trying to stop it, will delete once stopped
    * FAILED: terminated in error, no results
    * INVALID: somehow corrupt

## Socket.IO API

- Experimental, even more so than HTTP.
- The Socket.IO URL is also relative to `SIMSVC_ROOT` (`socket.io`
  under it).  This may require configuration in the client unless
  `SIMSVC_ROOT` is `/` (and there is no path rewriting).
- The server emits task-related events:
    * `launched` *jobid*,
    * `terminated {"job":` *jobid*, `"status":` *st*`}` where *st* is
      `"done"`, `"failed"` or `"cancelled"`.
- Later versions may introduce also commands.  Currently this is just
  server to client; client to server goes over HTTP.
