"""Miscellaneous utilities.
"""
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
