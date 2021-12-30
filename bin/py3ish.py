#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
usage: import py3ish

emulate Python 3 inside of Python 2, well enough for now
"""

# FIXME: help find and review diffs among scattered forks of shared defs


from __future__ import print_function

import argparse
import collections
import inspect
import shlex
import subprocess
import sys


#
# Define some Python idioms
#


# deffed in many files  # since Oct/2019 Python 3.7  # much too meta to pass Flake8 review
def f(formattable):
    """Emulate f"string"s"""

    f_ = inspect.currentframe()
    f_ = f_.f_back

    values_by_key = dict(f_.f_globals)
    values_by_key.update(f_.f_locals)

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
def subprocess_run(args, **kwargs):
    """
    Emulate Python 3 "subprocess.run"

    Don't help the caller remember to say:  stdin=subprocess.PIPE
    """

    # Trust the library, if available

    if hasattr(subprocess, "run"):
        run = subprocess.run(args, **kwargs)  # pylint: disable=subprocess-run-check

        return run

    # Emulate the library roughly, because often good enough

    kwargs_ = dict(**kwargs)  # args, cwd, stdin, stdout, stderr, shell, ...

    if "check" in kwargs:
        del kwargs_["check"]

    if ("input" in kwargs) and ("stdin" in kwargs):
        raise ValueError("stdin and input arguments may not both be used.")

    if "input" in kwargs:
        raise NotImplementedError("subprocess.run.input")

    sub = subprocess.Popen(args, **kwargs_)  # pylint: disable=consider-using-with
    (stdout, stderr) = sub.communicate()
    returncode = sub.poll()

    if "check" in kwargs:
        if returncode != 0:

            raise subprocess.CalledProcessError(
                returncode=returncode, cmd=args, output=stdout
            )

    run = argparse.Namespace(
        args=args, stdout=stdout, stderr=stderr, returncode=returncode
    )

    return run


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    """Print the Args, but to Stderr, not to Stdout"""

    sys.stdout.flush()
    print(*args, file=sys.stderr)
    sys.stderr.flush()  # like for kwargs["end"] != "\n"


# deffed in many files  # since Oct/2019 Python 3.7  # since Dec/2016 CPython 3.6
dict = collections.OrderedDict  # pylint: disable=redefined-builtin


# copied from:  git clone https://github.com/pelavarre/pybashish.git
