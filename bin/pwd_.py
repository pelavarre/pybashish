#!/usr/bin/env python3

"""
usage: pwd_.py [-h] [--brief] [--home] [-P]

show the os.environ["HOME"], by default just its "os.path.abspath"

optional arguments:
  -h, --help      show this help message and exit
  --brief         show the briefest abspath/ homepath/ relpath/ whatever
  --home          show the "~/..." "relpath" if in "~/" (default: True)
  -P, --physical  show the "realpath"s, not "abspath"s, of sym links

bugs:
  defaults to "--home", in the spirit of Bash "dirs +0" and Zsh "dirs -p", unlike their "pwd"s
  offers "--brief" and "--home", unlike Bash anywhere
  offers "--physical" like Linux, not just "-P" like Mac
  doesn't offer the explicit "--logical" of Linux, nor the "-L" of Mac and Linux

examples:
  pwd
  pwd -P
  pwd_.py --brief
  pwd_.py --home
"""
# FIXME: add "--verbose" a la "hostname"
# FIXME: somehow remember we don't want to abbreviate down to colliding "-" the unconventional "--"

from __future__ import print_function

import os
import sys

import argdoc


def main(argv):

    argv_tail = argv[1:] if argv[1:] else ["--home"]  # FIXME: more robust default
    args = argdoc.parse_args(argv_tail)

    pwd = os.environ["PWD"]
    abspath = os.path.abspath(pwd)
    realpath = os.path.realpath(pwd)

    cwd = os.getcwd()
    assert cwd == realpath

    path = realpath if args.physical else abspath  # FIXME: count -L -P contradictions
    briefpath = os_path_briefpath(path)
    homepath = os_path_homepath(path)

    printable = path
    if args.home:
        printable = homepath
    elif args.brief:  # FIXME: count -H -B contradictions
        printable = briefpath

    print(printable)


def os_path_briefpath(path, exemplar=None):

    exemplar = path if (exemplar is None) else exemplar

    bp = OsPathBriefPath(exemplar)
    briefpath = bp.briefpath(path)

    return briefpath


class OsPathBriefPath:
    def __init__(self, exemplar):
        # FIXME: do we ever want 'os.path.relpath(..., start='

        abbreviator = None

        abbreviators = (
            os.path.abspath,
            os.path.realpath,
            os.path.relpath,
            os_path_homepath,
        )
        for abbreviator_ in abbreviators:
            if abbreviator is None:

                abbreviator = abbreviator_

            elif len(abbreviator_(exemplar)) < len(abbreviator(exemplar)):

                abbreviator = abbreviator_

        self.abbreviator = abbreviator

    def briefpath(self, path):
        return self.abbreviator(path)


def os_path_homepath(path):

    home = os.path.realpath(os.environ["HOME"])
    homepath = path
    if (path == home) or path.startswith(home + os.path.sep):
        homepath = "~" + os.path.sep + os.path.relpath(path, start=home)

    return homepath


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
