#!/usr/bin/python3

"""A script to set up cov and mean defaults for the MPT model.
We use cov = R * Sigma^2 * R' where R is a random rotation
(Haar measure on SO(n), special_ortho_group from scipy.stats)
and Sigma is diagonal with independent standard normal components.
mean is also standard normal, independent components.

simsvc must be in PYTHONPATH.  Requires Numpy, Scipy and AIOHTTP
(used here because it supports Unix domain sockets).
"""

import logging, argparse, ssl

import asyncio, aiohttp
from aiohttp.helpers import netrc_from_env
from yarl import URL
from http import HTTPStatus
from socket import AddressFamily as AF

from scipy.stats import norm, special_ortho_group as rand_so

from simsvc.util import addrstr, tryrm
from simsvc.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

astr = Config.SIMSVC_ADDR

def gen_mean(n):
    return norm.rvs(size=n)

def gen_cov(n):
    r = rand_so.rvs(n)
    s2 = norm.rvs(size=n) ** 2
    return (r * s2) @ r.T

async def put(sess, base, name, val, ssl=None):
    kws = {} if ssl is None else {'ssl': ssl}
    async with sess.put(base + "default/" + name,
                        json=val.tolist(), **kws) as res:
        if res.status != HTTPStatus.NO_CONTENT:
            logger.info("%s: HTTP status %s: %s",
                        name, res.status, await res.text())

async def send(mean, cov, addr=None, af=None, base_url=None, ssl=None):
    kws = {}
    if hasattr(AF, 'AF_UNIX') and af == AF.AF_UNIX:
        kws['connector'] = aiohttp.UnixConnector(addr)
        base = "http://localhost/" if base_url is None else base_url
    else:
        base = "http://%s:%d/" % addr if base_url is None else base_url
        netrc = netrc_from_env()
        nca = netrc and netrc.authenticators(URL(base).host)
        if nca is not None:
            kws['auth'] = aiohttp.BasicAuth(nca[0], nca[-1])
    async with aiohttp.ClientSession(raise_for_status=True, trust_env=True,
                                     **kws) as sess:
        await put(sess, base, "mean", mean, ssl)
        await put(sess, base, "cov", cov, ssl)

if __name__ == '__main__':
    p = argparse.ArgumentParser(
        description="Initialize MPT covariance and mean")
    p.add_argument('-n', metavar='N', type=int, default=20,
                   help="portfolio size (default %(default)s)")
    p.add_argument('-c', '--cafile', default=None,
                   help="Root CA bundle for SSL verification")
    p.add_argument('-t', '--trust', action='store_true',
                   help="Disable SSL certificate verification")
    p.add_argument('url', nargs='?', default=None,
                   help="Simsvc base URL (with slash in the end)")
    args = p.parse_args()
    addr, af = addrstr(astr)
    if args.url is None or af != AF.AF_INET:
        logger.info("Connecting to addr=%s, af=%s", addr, af)
    sslc = False if args.trust else ssl.create_default_context(
        cafile=args.cafile)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send(gen_mean(args.n), gen_cov(args.n),
                                 addr, af, args.url, sslc))
