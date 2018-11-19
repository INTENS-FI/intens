#!/usr/bin/python3

"""A script to set up cov and mean defaults for the MPT model.
We use cov = R * Sigma^2 * R' where R is a random rotation
(Haar measure on SO(n), special_ortho_group from scipy.stats)
and Sigma is diagonal with independent standard normal components.
mean is likewise assumed standard normal, independent components.

simsvc must be in PYTHONPATH.  Requires Numpy, Scipy and AIOHTTP
(used here because it supports Unix domain sockets).
"""

import logging

import asyncio, aiohttp
from http import HTTPStatus
from socket import AddressFamily as AF

from scipy.stats import norm, special_ortho_group as rand_so

from simsvc.util import addrstr, tryrm
from simsvc.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

astr = Config.SIMSVC_ADDR
n = 20

def gen_mean(n):
    return norm.rvs(size=n)

def gen_cov(n):
    r = rand_so.rvs(n)
    s2 = norm.rvs(size=n) ** 2
    return (r * s2) @ r.T

async def put(sess, base, name, val):
    async with sess.put(base + "default/" + name, json=val.tolist()) as res:
        if res.status != HTTPStatus.NO_CONTENT:
            logger.info("%s: HTTP status %s: %s",
                        name, res.status, await res.text())

async def send(addr, af, mean, cov):
    if af == AF.AF_UNIX:
        conn = aiohttp.UnixConnector(addr)
        def sessf(**kws):
            return aiohttp.ClientSession(connector=conn, **kws)
        base = "http://localhost/"
    else:
        sessf = aiohttp.ClientSession
        base = "http://%s:%d/" % addr
    async with sessf(raise_for_status=True) as sess:
        await put(sess, base, "mean", mean)
        await put(sess, base, "cov", cov)

if __name__ == '__main__':
    addr, af = addrstr(astr)
    logger.info("Connecting to addr=%s, af=%s", addr, af)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send(addr, af, gen_mean(n), gen_cov(n)))
