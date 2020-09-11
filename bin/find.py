#!/usr/bin/env python3

r"""
usage: find.py [-h] [TOP] [HOW [HOW ...]]

print some words

positional arguments:
  TOP         the dir to walk (default: .)
  HOW         a hint of how to walk

optional arguments:
  -h, --help  show this help message and exit

bugs:
  searches "./" if called with no args, unlike mac bash
  leads each hit inside "./" with "" not with "./", unlike bash
  leads each hit inside "~/" with "~/" not with "$PWD", unlike bash
  hits the realpath of each sym link, not abspath, unlike bash

examples:
  find ~/bin/
  find ~/.bash_history  # file, not dir
  find /dev/null  # device, not dir
"""
# FIXME: rethink "find.py" bugs


from __future__ import print_function

import contextlib
import os
import signal
import sys

import argdoc


def main(argv):

    args = argdoc.parse_args()

    if args.hows:
        stderr_print("find.py: error: Got undefined hints: {}".format(args.hows))
        sys.exit(-1)

    try:
        print_os_walk_minpaths(args.top)
    except KeyboardInterrupt:
        sys.exit(0x80 + signal.SIGINT)  # "128+n if terminated by signal n" <= man bash
        # FIXME: Mac Zsh trace of this exit looks a little different for Bash "find" vs "find.py"


def print_os_walk_minpaths(top):

    top_ = "." if (top is None) else top
    top_realpath = os.path.realpath(top_)
    formatter = min_path_formatter(top_)

    print(formatter(top_realpath))
    walker = os_walk_sorted_relpaths(top)
    for relpath in walker:
        wherewhat = os.path.join(top_realpath, relpath)

        realpath = os.path.realpath(wherewhat)
        print(formatter(realpath))


# deffed in many files  # missing from docs.python.org
def os_path_homepath(path):
    """Return the ~/... relpath of a file or dir inside the Home, else the realpath"""

    home = os.path.realpath(os.environ["HOME"])

    homepath = path
    if path == home:
        homepath = "~"
    elif path.startswith(home + os.path.sep):
        homepath = "~" + os.path.sep + os.path.relpath(path, start=home)

    return homepath


# deffed in many files  # missing from docs.python.org
def os_walk_sorted_relpaths(top):
    """Walk the dirs and files in a top dir, returning their relpath's, sorted"""
    # FIXME: change to relpath closer to log messages

    top_ = "." if (top is None) else top
    top_realpath = os.path.realpath(top_)

    walker = os.walk(top_realpath)
    for (where, wheres, whats,) in walker:  # (dirpath, dirnames, filenames,)

        wheres[:] = sorted(wheres)  # sort these now, yield these later

        for what in sorted(whats):

            wherewhat = os.path.join(where, what)

            realpath = os.path.realpath(wherewhat)
            relpath = os.path.relpath(realpath, start=top_realpath)
            yield relpath

        for where_ in wheres:
            wherewhere = os.path.join(where, where_)
            yield wherewhere  # FIXME: delay yield dir till the walk starts into the dir


# deffed in many files  # missing from docs.python.org
def min_path_formatter(exemplar):
    """Choose the def that abbreviates this path most sharply: abs, real, rel, or home"""

    formatters = (
        os.path.abspath,
        os.path.realpath,
        os.path.relpath,
        os_path_homepath,
    )

    formatter = formatters[0]
    for formatter_ in formatters[1:]:
        if len(formatter_(exemplar)) < len(formatter(exemplar)):
            formatter = formatter_

    return formatter


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


# deffed in many files  # missing from docs.python.org
class BrokenPipeErrorSink(contextlib.ContextDecorator):
    """Cut unhandled BrokenPipeError down to sys.exit(1)

    More narrowly than:  signal.signal(signal.SIGPIPE, handler=signal.SIG_DFL)
    As per https://docs.python.org/3/library/signal.html#note-on-sigpipe
    """

    def __enter__(
        self,
    ):  # test with large Stdout cut sharply, such as:  find.py ~ | head
        return self

    def __exit__(self, *exc_info):
        (exc_type, exc, exc_traceback,) = exc_info
        if isinstance(exc, BrokenPipeError):  # catch this one

            null_fileno = os.open(os.devnull, os.O_WRONLY)
            os.dup2(null_fileno, sys.stdout.fileno())  # avoid the next one

            sys.exit(1)


if __name__ == "__main__":
    with BrokenPipeErrorSink():
        sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
