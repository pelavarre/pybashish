#!/usr/bin/env python3

r"""
usage: find.py [-h] [TOP] [HOW [HOW ...]]

print some words

positional arguments:
  TOP         the dir to walk
  HOW         a hint of how to walk

optional arguments:
  -h, --help  show this help message and exit

bugs:
  Bash Find of "./..." starts every line with "./"
  Bash Find of "~/..." starts every line with "$PWD/"
  Bash Find of sym links prints the abspath, not the realpath
  Mac Bash Find chokes if you don't give it any TOP
"""

from __future__ import print_function

import os
import sys

import argdoc

import bash

import pwd_


def main(argv):

    args = argdoc.parse_args()

    if args.hows:
        stderr_print("No hints yet defined, but got hints: {}".format(args.hows))
        sys.exit(-1)

    os_walk_print_homepath(top=args.top)


def os_walk_print_homepath(top):

    top_ = "." if (top is None) else top
    top_realpath = os.path.realpath(top_)

    bp = pwd_.OsPathBriefPath(exemplar=top_realpath)
    print(bp.briefpath(top_realpath))

    walker = os.walk(top_realpath)
    for (where, wheres, whats,) in walker:  # (dirpath, dirnames, filenames,)

        wheres[:] = sorted(wheres)

        for what in sorted(whats):
            wherewhat = os.path.join(where, what)

            print(bp.briefpath(wherewhat))


def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    with bash.BrokenPipeHandler():
        sys.exit(main(sys.argv))


# pulled from:  git clone https://github.com/pelavarre/pybashish.git
