#!/usr/bin/env python3

"""
usage: p.py [-h] HELLO

do good stuff

positional arguments:
  HELLO          an arg for us

optional arguments:
  -h, --help     show this help message and exit

examples:
  p.py 42
"""

import argdoc


def main():
    args = argdoc.parse_args()
    main.args = args
    print(args)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
