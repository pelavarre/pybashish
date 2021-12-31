#!/usr/bin/env python3

r"""
usage: echo.py [-h] [-n] [--verbose] [WORD ...]

print some words

positional arguments:
  WORD        a word to print

options:
  -h, --help  show this help message and exit
  -n          print just the words, don't add an end-of-line
  --verbose   print the "shlex.split" to "sys.stderr"

quirks:
  understand "-n" like bash or zsh echo, unlike sh echo

examples:
  echo 'Hello, Echo World!'
  echo -n '⌃ ⌥ ⇧ ⌘ ← → ↓ ↑ ' |hexdump -C
  echo.py --v 'Hello, Echo World!'
"""


from __future__ import print_function

import sys

import argdoc


def main():

    args = argdoc.parse_args()

    if args.verbose:
        print(args.words, file=sys.stderr)

    line = " ".join(args.words)

    if args.n:
        sys.stdout.write(line)
    else:
        print(line)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
