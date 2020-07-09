#!/usr/bin/env python3

"""
usage: wc.py [-h]

count lines and words and characters and bytes

optional arguments:
  -h, --help  show this help message and exit

bugs:
  acts like "wc -h" if called without args, unlike Bash "wc"

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
