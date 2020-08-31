#!/usr/bin/env python3

"""
usage: touch.py [-h] [FILE [FILE ...]]

mark a file as modified, or create a new empty file

positional arguments:
  FILE        a file to mark as modified

optional arguments:
  -h, --help  show this help message and exit

bugs:
  runs ahead and works with me, without mandating that I spell out the new name, unlike Bash "touch"

examples:
  touch  # creates "touch~1", then "touch~2", etc
"""

import os
import sys

import argdoc


def main():

    args = argdoc.parse_args()

    if not args.files:
        stderr_print("touch.py: error: touch of zero args not implemented")
        sys.exit(2)  # exit 2 from rejecting usage

    exit_status = None
    for file_ in args.files:

        if not os.path.exists(file_):
            with open(file_, "w"):
                pass
            continue

        try:
            os.utime(file_)
        except OSError as exc:
            stderr_print("touch.py: error: {}: {}".format(type(exc).__name__, exc))
            exit_status = 1

    sys.exit(exit_status)


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
