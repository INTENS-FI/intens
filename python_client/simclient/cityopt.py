"""Support for working with Cityopt CSV files.

Mainly optimisation problem definitions are supported.  Time series
are not.  Timestamps must be given as numbers (not ISO 8601).

This module requires Python 3 although expressions in Cityopt are
in Python 2 (Jython).
"""

import json, csv, builtins, ast
from enum import Enum, IntEnum, auto, unique
from collections import ChainMap, deque

class Kind(Enum):
    IN = auto()
    OUT = auto()
    EXT = auto()
    MET = auto()
    DV = auto()
    CON = auto()
    OBJ = auto()

def parse_ts(st):
    raise NotImplementedError("Time series not implemented")

@unique
class Type(Enum):
    INT = "Integer"
    FLOAT = "Double"
    STR = "String", lambda x: x
    TIME = "Timestamp"
    TS0 = "TimeSeries/step", parse_ts
    TS1 = "TimeSeries/linear", parse_ts
    INTS = "List of Integer"
    FLOATS = "List of Double"
    TIMES = "List of Timestamp"
    DYN = "Dynamic", eval

    def __new__(cls, value, parser=json.loads):
        o = object.__new__(cls)
        o._value_ = value
        o._parser = parser
        return o

    def parse(s, st):
        """Parse string st as this type."""
        return s._parser(st)

@unique
class Sense(IntEnum):
    MIN = -1
    MAX = 1

class Component:
    """Represents a Cityopt component in evaluation.

    This is constructed with a name _cname and a mapping _dict.  When
    attribute aname of the component is read but does not exist as an
    instance attribute, key qname(_cname, aname) is looked up in _dict.
    _cname and _dict are available as instance attributes and can be
    modified.
    """
    def __init__(s, cname, dict_):
        s._cname = cname
        s._dict = dict_

    def __getattr__(s, aname):
        try:
            return s._dict[qname(s._cname, aname)]
        except KeyError:
            raise AttributeError("Component '%s' has no attribute '%s'"
                                 % (s._cname, aname))

def qname(comp, name):
    return comp + "." + name if comp else name

def split_qname(qn):
    sp = qn.split(".")
    if len(sp) == 1:
        return None, qn
    elif len(sp) == 2:
        return tuple(sp)
    else:
        raise ValueError("Invalid qname '%s'" % qn)

# Globals for evaluating expressions in OptProb
glob = {'__builtins__': builtins}

def idems(dit):
    """Convenience function for iterating dict-likes.

    If dit.items is defined, call it and return the result.
    Otherwise return dit itself.
    """
    return dit.items() if hasattr(dit, 'items') else dit

def gen_eval(loc, exprs, update=False, undef=False):
    """Evaluate a dict-like of expressions.

    exprs is a dict or an iterable of (name, expr) pairs.  Each expr
    is evaluated (with eval) using module variable glob as globals and
    loc as locals.  Generates (name, value) pairs.  If update is true,
    the results are added to loc before yielding; it is equivalent to
    loc.update(gen_eval(loc, exprs)) but lets the caller also do
    something else with the results.  If undef is true, NameError and
    AttributeError are caught and silently skipped during evaluation
    (nothing is generated or inserted into loc).
    """
    for n, x in idems(exprs):
        if undef:
            try:
                v = eval(x, glob, loc)
            except (NameError, AttributeError):
                continue
        else:
            v = eval(x, glob, loc)
        if update:
            loc[n] = v
        yield n, v

class OptProb:
    """A Cityopt optimisation problem.

    Instance attributes are dictionaries qname -> value, where
    qname is a qualified name.
	ext	External parameters; value is the value (depends on type).
	dv	Decision variables; value is (Type, lb, ub) where
		Type is INT or FLOAT.  lb and ub are the bounds.
	in_c	Constant inputs; value is the value (depends on type).
	in_v	Variable inputs; value is the expression (usable in eval).
	out	Outputs; value is the Type.
	met	Metrics; value is the expression.
	con	Constraints; value is (expression, lb, ub).  The bounds
		lb and ub are numeric or None.
	obj	Objectives; value is (Sense, expression).
    In addition, components is the set of component names appearing in
    decision variables, inputs and outputs.

    The expressions listed above are compiled. Their original source code
    can be found in the dictionary src, indexed by (kind, qname).
    """
    def __init__(s):
        s.ext = {}
        s.dv = {}
        s.in_c = {}
        s.in_v = {}
        s.out = {}
        s.met = {}
        s.con = {}
        s.obj = {}
        s.components = set()
        s.src = {}

    def make_locals(s):
        """Create a local variable dictionary.

        This can be passed as locals to eval for evaluating expressions.
        It includes the external variables (ext) and constant inputs (in_c).
        Maps returned by different calls can be modified without affecting
        each other, but modification of ext or in_c affects all the maps.
        """
        loc = {}
        cm = ChainMap(loc, s.in_c, s.ext)
        for cn in s.components:
            loc[cn] = Component(cn, cm)
        return cm

    def gen_in(s, loc, dvs):
        """Compute simulation inputs.

        loc should be from make_locals.  It is updated from dvs and
        then by evaluating the variable inputs (in_v).  All inputs
        (constant and variable) are generated as (qname, value) pairs.
        """
        loc.update(dvs)
        yield from s.in_c.items()
        yield from gen_eval(loc, s.in_v, update=True)

    def eval_met(s, loc, out, **kws):
        """Compute metrics.

        loc should be from make_locals, extended with gen_inputs.
        It is updated from out (simulation outputs) and then by
        evaluating the metrics (met).  kws is passed to gen_eval.
        """
        loc.update(out)
        loc.update(gen_eval(loc, s.met, update=False, **kws))

    #TODO Constraint evaluation (pre and post simulation)

    def gen_obj(s, loc, **kws):
        """Compute objectives.

        loc should be from make_locals, extended with gen_inputs and
        eval_met.  Evaluates the objectives (from obj), generating
        (name, value) pairs.  The objectives are not inserted in loc.
        kws is passed to gen_eval.
        """
        return gen_eval(loc, ((n, x) for n, (sn, x) in s.obj.items()), **kws)

    def eval_obj(s, n, loc):
        _,x = s.obj[n]
        return eval(x, glob, loc)

    def _get_qname2kind(s):
        q2k = dict()
        q2k.update((n, Kind.EXT) for n in s.ext.keys())
        q2k.update((n, Kind.DV) for n in s.dv.keys())
        q2k.update((n, Kind.IN) for n in s.in_c.keys())
        q2k.update((n, Kind.IN) for n in s.in_v.keys())
        q2k.update((n, Kind.OUT) for n in s.out.keys())
        q2k.update((n, Kind.MET) for n in s.met.keys())
        q2k.update((n, Kind.OBJ) for n in s.obj.keys())
        return q2k

    def flag_prior_objs(s):
        """Determine which objectives can be evaluated prior to simulation.
        Returns list of booleans in the same order as 'obj'.
        """
        q2k = s._get_qname2kind()
        return [can_pre_eval(s.src[Kind.OBJ, n], q2k) for n in s.obj]

class _QNameCollector(ast.NodeVisitor):
    def __init__(s):
        s.qnames = set()
    def visit_Attribute(s, n, suffix=''):
        if isinstance(n.value, ast.Attribute):
            s.visit_Attribute(n.value, '.'+n.attr+suffix)
        elif isinstance(n.value, ast.Name):
            s.qnames.add(n.value.id+'.'+n.attr+suffix)
    def visit_Name(s, n):
        s.qnames.add(n.id)

def _expr_qnames(expr):
    """Set of qualified names referenced in the given expression."""
    qnc = _QNameCollector()
    qnc.visit(ast.parse(expr, mode='eval'))
    return qnc.qnames

# TODO compute transitive dependencies to enable metrics in prior objectives
def can_pre_eval(expr, q2k):
    return all(q2k[n] not in {Kind.OUT, Kind.MET, Kind.OBJ}
               for n in _expr_qnames(expr))

row_parsers = {}
def _parses(kind):
    def foo(f):
        row_parsers[kind] = f
        return f
    return foo

def _parse_expr(row):
    return compile(row['expression'],
                   "<%s>" % qname(row.get('component'), row['name']),
                   'eval')

@_parses(Kind.EXT)
def _parse_value(row):
    return Type(row['type']).parse(row['value'])

@_parses(Kind.IN)
def _parse_in(row):
    if row.get('expression'):
        return True, _parse_expr(row)
    else:
        return False, _parse_value(row)

@_parses(Kind.OUT)
def _parse_out(row):
    return Type(row['type'])

@_parses(Kind.MET)
def _parse_met(row):
    return _parse_expr(row)

@_parses(Kind.DV)
def _parse_dv(row):
    typ = Type(row['type'])
    return typ, typ.parse(row['lower']), typ.parse(row['upper'])

@_parses(Kind.CON)
def _parse_con(row):
    def _parse_bd(s):
        return json.loads(s) if s else None
    return (_parse_expr(row),
            _parse_bd(row.get('lower')), _parse_bd(row.get('upper')))

@_parses(Kind.OBJ)
def _parse_obj(row):
    return Sense[row['type'].upper()], _parse_expr(row)

def read_op(fname):
    """Read an OptProb from file fname.
    """
    p = OptProb()
    with open(fname) as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            kind = Kind[row['kind'].upper()]
            name = row['name']
            if kind in (Kind.DV, Kind.IN, Kind.OUT):
                comp = row.get('component')
            else:
                comp = None
            qn = qname(comp, name)
            v = row_parsers[kind](row)
            if comp:
                p.components.add(comp)
            if kind == Kind.IN:
                is_v, d = v
                (p.in_v if is_v else p.in_c)[qn] = d
            else:
                getattr(p, kind.name.lower())[qn] = v
            if row['expression']:
                p.src[kind, qn] = row['expression']
    return p
