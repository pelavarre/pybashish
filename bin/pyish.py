#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
usage: pyish.py

emulate Python 3 inside of Python 2, well enough for now

bugs:
  cd pybashish/ && make  # foolishly insists this docstring should be an argdoc
"""

from __future__ import print_function

import argparse
import collections
import contextlib
import inspect
import shlex


# deffed in many files  # since Oct/2019 Python 3.7
def f(formattable):
    """Emulate f"string"s"""

    f = inspect.currentframe()
    f = f.f_back

    values_by_key = dict(f.f_globals)
    values_by_key.update(f.f_locals)

    formatted = formattable.format(**values_by_key)

    return formatted


# deffed in many files  # since Oct/2019 Python 3.8
def shlex_join(argv):
    """Undo enough of the "shlex.split" to log its work reasonably well"""

    rep = " ".join((repr(_) if (" " in _) else _) for _ in argv)

    if '"' not in rep:  # like don't guess what "'$foo'" means
        try:
            if shlex.split(rep) == argv:
                return rep
        except ValueError:
            pass

    rep = repr(argv)
    return rep


# deffed in many files  # since Sep/2015 Python 3.5
def subprocess_run(*args, **kwargs):
    """Emulate Python 3 "subprocess.run" """

    args_ = args[0] if args else kwargs["args"]
    kwargs_ = dict(**kwargs)  # args, cwd, stdin, stdout, stderr, shell, ...

    if ("input" in kwargs) and ("stdin" in kwargs):
        raise ValueError("stdin and input arguments may not both be used.")

    if "input" in kwargs:
        del kwargs_["input"]
        kwargs_["stdin"] = io.StringIO(kwargs["input"])

    sub = subprocess.Popen(*args, **kwargs_)
    (stdout, stderr,) = sub.communicate()
    returncode = sub.poll()

    ran = argparse.Namespace(
        args=args_, stdout=stdout, stderr=stderr, returncode=returncode,
    )

    return ran


# deffed in many files  # but not in docs.python.org
def stderr_print(*args):
    print(*args, file=sys.stderr)


dict = collections.OrderedDict
