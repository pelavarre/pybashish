#!/usr/bin/env python3

"""
usage: mv.py [-h] [-i] [FILE]

rename a file (make it not found)

positional arguments:
  FILE        the file to duplicate (default: last modified in cwd, else '/dev/null')

options:
  -h, --help  show this help message and exit
  -i          ask before replacing some other file

quirks:
  chooses new file names like Emacs would:  'null', 'null~', 'null~2~', ...
  moves without changing the name, when the Cwd doesn't already contain the name
  moves from Remote hostname:path on request, not only from LocalHost
  defaults '-i' to True, and gives you no way to turn it off

examples:
  mv.py  # renames the last modified file of cwd (makes it not found)
  mv.py -  # captures a copy of Stdin (same as 'cp.py -')
  mv.py /dev/null  # fails for insufficient privilege
  mv.py /  # fails for insufficient privilege
"""

# FIXME: add mv -u, --update for move if new or fresher
# FIXME: synch help and code across chmod.py cp.py mv.py rm.py touch.py ...
# FIXME: spec & test the two arg case of 'overwrite ...? (y/n [n]) ' moving same file


import sys

import argdoc


def main():
    args = argdoc.parse_args()
    sys.stderr.write("{}\n".format(args))
    sys.stderr.write("{}\n".format(argdoc.format_usage().rstrip()))
    sys.stderr.write("mv.py: error: not implemented\n")
    sys.exit(2)  # exit 2 from rejecting usage


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
