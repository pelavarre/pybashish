#!/usr/bin/env python3

"""
usage: mv.py [-h] [-i] [FILE]

rename a file (make it not found)

positional arguments:
  FILE        the file to rename (default: last modified in cwd)

optional arguments:
  -h, --help  show this help message and exit
  -i          ask before replacing some other file

quirks:
  runs ahead and works, without making you spell out the new name, unlike Bash "mv"
  increments the name, such as:  touch it~41~ && touch it && mv.py  # it~41~ it~42~
  requires two args to rename files that aren't files or dirs below the root dir

examples:
  mv.py  # renames the last modified file of cwd (makes it not found)
  mv.py -  # waits for stdin, then does nothing (a la cat >/dev/null)
  mv.py itself  # renames the file to "itself~1~", etc
  mv.py /dev/null  # fails because insufficient privilege
  mv.py /  # fails because insufficient privilege
"""


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
