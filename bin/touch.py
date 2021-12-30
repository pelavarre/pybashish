#!/usr/bin/env python3

"""
usage: touch.py [-h] [FILE [FILE ...]]

mark a file as modified, or create a new empty file

positional arguments:
  FILE        a file to mark as modified (default: copies zero bytes from latest in cwd)

optional arguments:
  -h, --help  show this help message and exit

quirks:
  chooses a new file name for you, when none provided, unlike bash "touch"

examples:
  touch  # creates "touch~1~", then "touch~2~", etc
"""

# TODO: layer over:  os.utime

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
            with open(file_, mode="w"):
                pass
            continue

        try:
            os.utime(file_)
        except OSError as exc:
            stderr_print("touch.py: error: {}: {}".format(type(exc).__name__, exc))
            exit_status = 1

    sys.exit(exit_status)


#
# Define some Python idioms
#


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    """Print the Args, but to Stderr, not to Stdout"""

    sys.stdout.flush()
    print(*args, file=sys.stderr)
    sys.stderr.flush()  # like for kwargs["end"] != "\n"


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
