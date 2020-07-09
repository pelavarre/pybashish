#!/usr/bin/env python3

"""
usage: grep.py [-h]

search for stuff

optional arguments:
  -h, --help  show this help message and exit

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
