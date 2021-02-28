#!/usr/bin/env python3

"""
usage: sort.py [-h]

sort lines

optional arguments:
  -h, --help  show this help message and exit

quirks:
  sorts tabs as different than spaces
  sorts some spaces ending a line as different than none ending a line

examples:
  Oh no! No examples disclosed!! 💥 💔 💥
"""
# FIXME: doc -k$N,$N and -n and maybe little else is worth learning
# FIXME: ass -k-1,-1 for negative field indexing
# FIXME: think into the mess at "sort" vs "LC_ALL=C sort"


import sys

import argdoc


def main():
    args = argdoc.parse_args()
    sys.stderr.write("{}\n".format(args))
    sys.stderr.write("{}\n".format(argdoc.format_usage().rstrip()))
    sys.stderr.write("sort.py: error: not implemented\n")
    sys.exit(2)  # exit 2 from rejecting usage


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
