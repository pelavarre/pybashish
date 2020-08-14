#!/usr/bin/env python3

"""
usage: touch.py [-h] [FILE [FILE ...]]

mark a file as modified, or create a new empty file

positional arguments:
  FILE        a file to mark as modified

optional arguments:
  -h, --help  show this help message and exit

bugs
  runs ahead and works with me, without mandating that I spell out the new name, unlike Bash "touch"

examples:
  touch  # creates "touch~1", then "touch~2", etc
"""


import sys

import argdoc


def main():
    args = argdoc.parse_args()
    sys.stderr.write("{}\n".format(args))
    sys.stderr.write("{}\n".format(argdoc.format_usage().rstrip()))
    sys.stderr.write("touch.py: error: not implemented\n")
    sys.exit(2)  # exit 2 from rejecting usage


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
