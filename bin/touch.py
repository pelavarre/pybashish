#!/usr/bin/env python3

"""
usage: touch.py [-h] [FILE]

mark a file as modified, or create a new empty file

positional arguments:
  FILE        the file to mark as modified

optional arguments:
  -h, --help  show this help message and exit

bugs
  runs ahead and works with me, without mandating that I spell out the new name, unlike Bash "touch"

examples:
  touch  # creates "touch~1", then "touch~2", etc
"""

import argdoc


def main():
    args = argdoc.parse_args()
    print(args)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
