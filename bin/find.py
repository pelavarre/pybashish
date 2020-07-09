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
  searches "./" if called with no args, unlike Mac Bash
  leads each hit inside "./" with "" not "./", unlike Bash
  leads each hit inside "~/" with "~/" not "$PWD", unlike Bash
  hits the realpath of each sym link, not abspath, unlike Bash

examples:
  find ~/bin/
  find /dev/null
"""
# FIXME: rethink bugs

from __future__ import print_function

import os
import sys

import argdoc

import cat  # for cat.BrokenPipeSink

import pwd_  # for pwd_.OsPathBriefPath


def main(argv):

    args = argdoc.parse_args()

    if args.hows:
        stderr_print("error: find.py: Got undefined hints: {}".format(args.hows))
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


def stderr_print(*args):  # deffed in many files
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    with cat.BrokenPipeSink():
        sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
