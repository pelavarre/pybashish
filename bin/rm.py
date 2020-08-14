#!/usr/bin/env python3

"""
usage: rm.py [-h]

move a file to the ../__jqd-trash/ dir

optional arguments:
  -h, --help  show this help message and exit

bugs:
  don't rush to reclaim disk space, like Bash "rm" does

examples:
  Oh no! No examples disclosed!! 💥 💔 💥
"""

import argdoc


def main():
    args = argdoc.parse_args()
    print(args)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
