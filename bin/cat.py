#!/usr/bin/env python3

"""
usage: cat.py [-h] [-n] [FILE [FILE ...]]

copy ("cat"enate) files to standard output

positional arguments:
  FILE          a file to copy

optional arguments:
  -h, --help    show this help message and exit
  -n, --number  number each line of output
"""


import os
import sys

import argdoc


def main():

    args = argdoc.parse_args()

    line_index = 1
    for relpath in args.files:  # FIXME: evade Linux-specific "/dev/stdin"
        relpath = "/dev/stdin" if (relpath == "-") else relpath

        if not os.path.exists(relpath):
            try:
                open(relpath, "rt")
            except FileNotFoundError as exc:
                stderr_print("{}: {}".format(type(exc).__name__, exc))
                sys.exit(1)

        if not args.number:

            with open(relpath, "rb") as reading:
                fileno = sys.stdout.fileno()
                os.write(
                    fileno, reading.read()
                )  # stop asking for buffers of whole files

        else:

            with open(relpath, "r") as reading:
                for line in reading.readlines():  # stop implying buffers of whole files
                    print("{:6}\t{}".format(line_index, line.rstrip()))
                    line_index += 1


if __name__ == "__main__":
    main()


# pulled from:  git clone https://github.com/pelavarre/pybashish.git
