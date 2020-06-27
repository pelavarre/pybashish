#!/usr/bin/env python3

r"""
usage: echo.py [-h] [-n] [WORD [WORD ...]]

print some words

positional arguments:
  WORD         a word to print

optional arguments:
  -h, --help  show this help message and exit
  -n  print just the words, don't add an end-of-line
"""

from __future__ import print_function

import sys

import argdoc


def main(argv):

    args = argdoc.parse_args()

    line = " ".join(args.words)

    if args.n:
        sys.stdout.write(line)
    else:
        print(line)


if __name__ == "__main__":
    sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
