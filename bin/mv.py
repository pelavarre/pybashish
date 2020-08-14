#!/usr/bin/env python3

"""
usage: mv.py [-h] [-i] FILE

rename a file

positional arguments:
  FILE        the file to rename

optional arguments:
  -h, --help  show this help message and exit
  -i          ask before replacing some other file

bugs:
  acts like "mv -h" if called without "-i" arg, unlike Bash "mv"
  runs ahead and works with me, without mandating that I spell out the new name, unlike Bash "mv"

examples:
  mv stdin~9  # changes the name of this file to "stdin~10"
"""

import argdoc


def main():
    args = argdoc.parse_args()
    print(args)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
