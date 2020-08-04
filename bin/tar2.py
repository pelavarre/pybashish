#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
usage: tar2.py [-h] [-x] [-t] [-v] [-k] [-f FILE]

pick files and dirs out of a top dir compressed as ".tgz"

optional arguments:
  -h, --help  show this help message and exit
  -x          extract every file
  -t          say it loud, you have not chosen -x
  -v          trace each file or dir name found inside to Stderr
  -k          decline to replace pre-existing output files
  -f FILE     name the file to uncompress

bugs:
  accepts only -tvf and -tvkf as options
  lets you type out just "tvf" or "tvkf" without their leading "-" dash
  prints only the name for -tvf, not all the "ls -al" columns
  prints all the dirs for -tvf, not only the top dir
  lists to Stderr, not to classic Stdout
  extracts to Stdout, not to the Tgz member name

examples:
  rm -fr dir/ dir.tgz
  mkdir -p dir/a/b/c dir/p/q/r
  echo hello >dir/a/b/d
  echo goodbye > dir/a/b/e
  tar czf dir.tgz dir/
  tar2.py tvf dir.tgz
  tar2.py xvkf dir.tgz | wc  # 2 lines, 2 words, 14 bytes
"""

from __future__ import print_function

import os
import sys
import tarfile

import argdoc

import pyish


def main(argv):

    # Parse the command line

    parseables = list(argv[1:])
    if argv[1:] and not argv[1].startswith("-"):
        parseables[0] = "-{}".format(argv[1])

    args = argdoc.parse_args(parseables if parseables else "--help".split())

    # FIXME: factor this out as method, update "tar.py" too

    tvf = args.t and args.v and args.file
    xvkf = args.x and args.v and args.k and args.file

    if (not tvf) and (not xvkf):

        str_args = ""
        for concise in "txvk":
            if getattr(args, concise):
                str_args += concise
        if args.file is not None:
            str_args += "f"
        str_args = "-{}".format(str_args) if str_args else ""

        stderr_print("usage: tar2.py: [-h] (-tvf|xvkf) FILE")
        if not str_args:
            stderr_print("tar2.py: error: too few arguments")
        else:
            stderr_print("tar2.py: error: unrecognized arguments: {}".format(str_args))
        sys.exit(2)  # FIXME: comment magic 2

    # Visit each dir or file inside the Tar file

    with tarfile.open(args.file) as untarring:

        names = untarring.getnames()
        for name in names:
            member = untarring.getmember(name)

            # Trace the visit

            if member.isdir():
                print(name + os.sep, file=sys.stderr)
            else:
                print(name, file=sys.stderr)

                # Extract the bytes of a file

                if args.x:

                    incoming = untarring.extractfile(name)
                    try:
                        file_bytes = incoming.read()
                    finally:
                        incoming.close()

                    os.write(sys.stdout.fileno(), file_bytes)


# deffed in many files  # but not in docs.python.org
def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
