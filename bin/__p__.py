#!/usr/bin/env python3

"""
usage: __p__.py [-h]

stub out the next bash verb you'll define

optional arguments:
  -h, --help  show this help message and exit

quirks:
  Oh no! No quirks disclosed!! 💥 💔 💥

examples:
  export PATH="${PATH:+$PATH:}$PWD/bin"
  __p__.py -h
  cp -ip bin/__p__.py bin/getstuffdone.py
  git add bin/getstuffdone.py
  git commit -m 'WIP getstuffdone'
"""


import sys

import argdoc


def main():
    args = argdoc.parse_args()
    sys.stderr.write("{}\n".format(args))
    sys.stderr.write("{}\n".format(argdoc.format_usage().rstrip()))
    sys.stderr.write("__p__.py: error: not implemented\n")
    sys.exit(2)  # exit 2 from rejecting usage


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
