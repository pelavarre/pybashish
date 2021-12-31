#!/usr/bin/env python3

"""
usage: rm.py [-h] [FILE ...]

move a file to the ../__jqd-trash/ dir

positional arguments:
  FILE        a file to trash (default: last modified of cwd)

options:
  -h, --help  show this help message and exit

quirks:
  don't rush to reclaim disk space, like Bash "rm" does

examples:
  Oh no! No examples disclosed!! 💥 💔 💥
"""


import sys

import argdoc


def main():
    args = argdoc.parse_args()
    sys.stderr.write("{}\n".format(args))
    sys.stderr.write("{}\n".format(argdoc.format_usage().rstrip()))
    sys.stderr.write("rm.py: error: not implemented\n")
    sys.exit(2)  # exit 2 from rejecting usage


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
