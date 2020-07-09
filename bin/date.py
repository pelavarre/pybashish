#!/usr/bin/env python3

"""
usage: date.py [-h]

show what time it is, of which day

optional arguments:
  -h, --help  show this help message and exit

bugs:
  give the available precision, don't floor to the last second like Bash

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
