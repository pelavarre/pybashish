#!/usr/bin/env python3

"""
usage: chmod.py [-h] [-R] MODE [TOP ...]

change the permissions on a file or dir

positional arguments:
  MODE             one of r"[ugo]*[-+=][rwx]+", or more arcane choices
  TOP              the file or dir to change permissions at

options:
  -h, --help       show this help message and exit
  -R, --recursive  change the dirs and files inside of top dirs, not just the top dir

quirks:
  doesn't implement the more arcane choices

examples:
  chmod.py -R ugo+rw /dev/null
  chmod.py ugo+rw /dev/null -R
  chmod.py -rw /dev/null
  chmod.py +rw /dev/null
  chmod.py =rw /dev/null
"""


import sys

import argdoc


def main(argv):

    chmod_argv_tail = argv[1:]
    if argv[1:]:
        if argv[1].startswith("-") and not argv[1].startswith("-R"):
            chmod_argv_tail[0:0] = ["--"]

    args = argdoc.parse_args(chmod_argv_tail)

    sys.stderr.write("{}\n".format(args))
    sys.stderr.write("{}\n".format(argdoc.format_usage().rstrip()))
    sys.stderr.write("chmod.py: error: not implemented\n")
    sys.exit(2)  # exit 2 from rejecting usage


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
