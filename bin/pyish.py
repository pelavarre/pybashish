#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
usage: pyish.py

emulate Python 3 inside of Python 2, well enough for now

quirks:
  cd pybashish/ && make  # foolishly insists this docstring should be an argdoc
"""
# FIXME: help find and review diffs among scattered forks of such shared defs
# FIXME: rename "guess_stdout_columns" to "sys_stdout_guess_columns"


from __future__ import print_function

import argparse
import collections
import inspect
import io
import shlex
import subprocess
import sys


#
# Git-track some Python idioms here
#


# deffed in many files  # since Oct/2019 Python 3.7  # much too meta to pass Flake8 review
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


# FIXME: def str_removesuffix


# deffed in many files  # since Sep/2015 Python 3.5
def subprocess_run(*args, **kwargs):
    """
    Emulate Python 3 "subprocess.run"

    Leave in place the standard defaults of stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr
    Although most callers mean to say stdin=subprocess.PIPE
    """

    args_ = args[0] if args else kwargs["args"]
    kwargs_ = dict(**kwargs)  # args, cwd, stdin, stdout, stderr, shell, ...

    if ("input" in kwargs) and ("stdin" in kwargs):
        raise ValueError("stdin and input arguments may not both be used.")

    if "input" in kwargs:  # FIXME FIXME FIXME: this doesn't work??
        del kwargs_["input"]
        kwargs_["stdin"] = io.StringIO(kwargs["input"])

    sub = subprocess.Popen(*args, **kwargs_)
    (stdout, stderr,) = sub.communicate()
    returncode = sub.poll()

    ran = argparse.Namespace(
        args=args_, stdout=stdout, stderr=stderr, returncode=returncode,
    )

    return ran


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    sys.stdout.flush()
    # print(*args, **kwargs, file=sys.stderr)  # SyntaxError in Python 2
    print(*args, file=sys.stderr)
    sys.stderr.flush()


# deffed in many files  # since Oct/2019 Python 3.7  # since Dec/2016 CPython 3.6
dict = collections.OrderedDict


# copied from:  git clone https://github.com/pelavarre/pybashish.git
