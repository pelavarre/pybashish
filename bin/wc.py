#!/usr/bin/env python3

"""
usage: wc.py [-h] [-L] [-l] [-m] [-c] [FILE [FILE ...]]

count lines and words and characters and bytes

positional arguments:
  FILE                   a file to examine

optional arguments:
  -h, --help             show this help message and exit
  -L, --max-line-length  count max characters per line
  -l, --lines            count lines
  -m, --chars            count characters
  -c, --bytes            count bytes

bugs:
  acts like "wc -L -l" if called without args, unlike Bash "wc"

popular bugs:
  does prompt once for stdin, like bash "grep -R", unlike bash "fmt"
  accepts only the "stty -a" line-editing c0-control's, not the "bind -p" c0-control's

examples:
  Oh no! No examples disclosed!! 💥 💔 💥
"""


import sys

import argdoc


def main():
    args = argdoc.parse_args()
    sys.stderr.write("{}\n".format(args))
    sys.stderr.write("{}\n".format(argdoc.format_usage().rstrip()))
    sys.stderr.write("wc.py: error: not implemented\n")
    sys.exit(2)  # exit 2 from rejecting usage


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
