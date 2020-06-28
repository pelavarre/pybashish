#!/usr/bin/env python3

r"""
usage: clips.py [-h] [REGEX [REGEX ...]]

search out some texts clipped from wherever

positional arguments:
  REGEX       a regex to match

optional arguments:
  -h, --help  show this help message and exit
"""

from __future__ import print_function

import sys

import argdoc  # FIXME: packaging


def main(argv):

    args = argdoc.parse_args()

    print(args)  # FIXME: do good stuff


def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
