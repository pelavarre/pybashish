#!/usr/bin/env python3

"""
usage: mkdir.py [-h] [-p] [DIR [DIR ...]]

create a dir

positional arguments:
  DIR            a dir to create (or to mention as already existing)

optional arguments:
  -h, --help     show this help message and exit
  -p, --parents  create the dir, its parent dir, and ancestors, if need be

bugs:
  says "dir exists" when
  runs ahead and works with me, without mandating that I spell out the new name, unlike Bash "mkdir"
  says "dir exists", not traditional "file exists", if dir exists already

examples:
  mkdir  # creates "mkdir~1~", then "mkdir~2~", etc
"""


import os
import sys

import argdoc


def main():

    args = argdoc.parse_args()

    if not args.dirs:
        stderr_print("mkdir.py: error: mkdir of zero args not implemented")
        sys.exit(2)  # exit 2 from rejecting usage

    exit_status = None
    for dir_ in args.dirs:

        if os.path.isdir(dir_):
            if not args.parents:
                stderr_print(
                    "mkdir.py: error: cannot create a dir that exists: {}".format(dir_)
                )
                exit_status = 1
            continue

        try:
            if args.parents:
                os.makedirs(dir_)
            else:
                os.mkdir(dir_)
        except OSError as exc:
            stderr_print("mkdir.py: error: {}: {}".format(type(exc).__name__, exc))
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
