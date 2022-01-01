#!/usr/bin/env python3

"""
usage: zsh.py [-h]

tweak up your experience of Zsh

options:
  -h, --help            show this help message and exit

quirks:
  Oh no! No quirks disclosed!! 💥 💔 💥

examples:
  zsh.py -h
"""


import sys

import argdoc


def main():
    args = argdoc.parse_args()
    sys.stderr.write("{}\n".format(args))
    sys.stderr.write("{}\n".format(argdoc.format_usage().rstrip()))
    sys.stderr.write("zsh.py: error: not implemented\n")
    sys.exit(2)  # exit 2 from rejecting usage


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
