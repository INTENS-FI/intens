"""Attempt to use asyncio.

Failed because asyncio subprocess support requires setup in the main
thread, which we do not control in the Dask worker.
"""

from concurrent.futures import CancelledError
import asyncio, os, traceback as tb

import dask

async def run_it(spec):
    #TODO
    script = os.path.join(os.path.dirname(__file__), "sum.sh")
    proc = await asyncio.create_subprocess_exec(
        script, *(str(spec.inputs[n]) for n in ['x', 'y']),
        cwd=spec.workdir)
    out, err = await proc.communicate()
    if err:
        raise RuntimeError(err)
    else:
        return {'sum': int(out)}

async def poll_cancel(run, cancel):
    while not cancel.get():
        await asyncio.sleep(5)
    run.cancel()

async def main(spec, cancel):
    run = asyncio.ensure_future(run_it(spec))
    watch = asyncio.ensure_future(poll_cancel(run, cancel))
    try:
        return await run
    finally:
        watch.cancel()
    

@dask.delayed
def task(spec, cancel):
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(main(spec, cancel))
    except:
        tb.print_exc()
        raise
