#!/usr/bin/env python3

"""
usage: cat.py [-h] [-n] [FILE [FILE ...]]

copy ("cat"enate) files to standard output

positional arguments:
  FILE          a file to copy

optional arguments:
  -h, --help    show this help message and exit
  -n, --number  number each line of output

bugs:
  doesn't forward interactive input lines immediately
"""

from __future__ import print_function

import os
import sys

import argdoc


def main():

    args = argdoc.parse_args()
    relpaths = args.files if args.files else ["-"]

    if "-" in relpaths:
        stderr_print("Press ⌃D EOF to quit")
        stderr_print("bug: doesn't forward interactive input lines immediately")

    # Visit each file

    line_index = 1
    for relpath in relpaths:  # FIXME: evade Linux-specific "/dev/stdin"
        relpath = "/dev/stdin" if (relpath == "-") else relpath

        # Fail fast if file not found

        if not os.path.exists(relpath):  # FIXME: stop branching on os.path.exists
            try:
                with open(relpath, "rt"):
                    pass
            except FileNotFoundError as exc:
                stderr_print("{}: {}".format(type(exc).__name__, exc))
                sys.exit(1)

        # Number on the right side of 6 columns, then a hard tab 2 column separator, then the line

        if args.number:

            with open(relpath, "r") as reading:
                for (
                    line
                ) in reading.readlines():  # FIXME: stop implying buffers of whole files
                    print("{:6}\t{}".format(line_index, line.rstrip()))
                    line_index += 1

            continue

        # Copy binary out without numbering the lines

        with open(relpath, "rb") as reading:
            fileno = sys.stdout.fileno()
            os.write(
                fileno, reading.read()
            )  # FIXME: stop asking for buffers of whole files


def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main()


# pulled from:  git clone https://github.com/pelavarre/pybashish.git
