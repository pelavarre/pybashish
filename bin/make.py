#!/usr/bin/env python3

"""
usage: make.py [-h]

figure out how to make more things from some things

options:
  -h, --help  show this help message and exit

quirks:
  don't understand most of what the real "make" knows

examples:
  Oh no! No examples disclosed!! 💥 💔 💥
"""


import sys

import argdoc


def main():
    _ = argdoc.parse_args()
    sys.stderr.write("{}\n".format(argdoc.format_usage().rstrip()))
    sys.stderr.write("make.py: error: not implemented\n")
    sys.exit(2)  # exit 2 from rejecting usage


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
