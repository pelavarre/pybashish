#!/usr/bin/env python3

"""
usage: pwd.py [-h] [--briefpath] [--homepath] [-L] [-P]

show the os.environ["HOME"], by default just its "os.path.abspath"

optional arguments:
  -h, --help      show this help message and exit
  --briefpath     show the briefest abspath/ homepath/ relpath/ whatever
  --homepath      show the "os.path.relpath" as "~/...", a la Bash "dirs + 0"
  -L, --logical   show the "os.path.abspath"
  -P, --physical  show the "os.path.realpath", like walk through symbolic links

bugs:
  offers "--briefpath" and "--homepath", unlike Bash
  offers "--logical" and "--physical" like Linux, not just "-L" and "-P" like Mac
"""
# FIXME: add "--verbose" a la "hostname"
# FIXME: somehow remember we don't want to abbreviate down to colliding "-" the unconventional "--"

from __future__ import print_function

import os

import argdoc


def main():

    args = argdoc.parse_args()

    pwd = os.environ["PWD"]
    abspath = os.path.abspath(pwd)
    realpath = os.path.realpath(pwd)

    cwd = os.getcwd()
    assert cwd == realpath

    path = realpath if args.physical else abspath  # FIXME: count -L -P contradictions
    briefpath = os_path_briefpath(path)
    homepath = os_path_homepath(path)

    printable = path
    if args.homepath:
        printable = homepath
    elif args.briefpath:  # FIXME: count -H -B contradictions
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
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
