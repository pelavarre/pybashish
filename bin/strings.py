#!/usr/bin/env python3

"""
usage: strings.py [-h] [FILE ...]

pick out bits from files

positional arguments:
  FILE        a file to pick over (default: stdin)

options:
  -h, --help  show this help message and exit

quirks:
  don't just pick out printables from binaries, in the way of the classic "strings" app

examples:
  cat bin/strings.py |bin/strings.py
"""


import sys

import argdoc


def main():
    args = argdoc.parse_args()
    sys.stderr.write("{}\n".format(args))
    sys.stderr.write("{}\n".format(argdoc.format_usage().rstrip()))
    sys.stderr.write("strings.py: error: not implemented\n")
    sys.exit(2)  # exit 2 from rejecting usage


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
