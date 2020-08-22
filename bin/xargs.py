#!/usr/bin/env python3

r"""
usage: xargs.py [-h]

split and rejoin the words of all lines of input into one line of output

optional arguments:
  -h, --help  show this help message and exit

examples:
  echo 'a  b  c$  d  e$$f  g$' | tr '$' '\n' | xargs.py  # join
"""


import sys

import argdoc


def main():
    """Run from the command line"""

    _ = argdoc.parse_args()

    stdin = sys.stdin.read()
    stdout = "{}\n".format(" ".join(stdin.split()))

    sys.stdout.write(stdout)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
