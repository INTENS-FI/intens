"""Miscellaneous utilities.
"""
import os
from http import HTTPStatus

empty_response = ("", HTTPStatus.NO_CONTENT)

def boolstr(s):
    """Interpret string s as a Boolean.

    This is intended for interpreting HTTP query parameters.  "False",
    "no" or "off" in any case and any representation of the
    integer 0 count as false, everything else - such as the empty
    string - counts as true.
    """
    if s.lower() in ["false", "no", "off"]:
        return False
    try:
        return bool(int(s))
    except ValueError:
        return True

def addrstr(astr):
    """Parse string astr as a socket address.

    Return (addr, af) where af is a socket.AddressFamily and the type
    of addr depends on af (see documentation of the socket module).
    If astr contains a slash it is interpreted as the file name of a
    AF_UNIX socket.  Otherwise the syntax is host:port for an
    AF_INET socket.
    """
    from socket import AddressFamily as AF
    if "/" in astr:
        return astr, AF.AF_UNIX
    else:
        addr, ps = astr.split(":")
        return (addr, int(ps)), AF.AF_INET

def tryrm(fname):
    """Remove file fname if it exists.
    No-op if it doesn't.
    """
    try:
        os.remove(fname)
    except FileNotFoundError:
        pass
