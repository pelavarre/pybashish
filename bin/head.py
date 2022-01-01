#!/usr/bin/env python3

"""
usage: head.py [-h] [-n COUNT] [FILE ...]

show just the leading lines of a file

positional arguments:
  FILE                  the file to drop trailing lines from (default: stdin)

options:
  -h, --help            show this help message and exit
  -n COUNT, --lines COUNT
                        how many leading lines to show (default: 10)

quirks:
  takes a count led by "+" as how many trailing lines to drop
  takes "-5" or "+9" and such, like mac "tail", unlike bash "head"

unsurprising quirks:
  prompts for stdin, like mac bash "grep -R .", unlike bash "head"
  accepts the "stty -a" line-editing c0-control's, not also the "bind -p" c0-control's
  takes file "-" as meaning "/dev/stdin", like linux "head -", unlike mac "head -"

examples:
  head.py /dev/null
  head.py head.py
  head.py -5 head.py
  head.py -n 5 head.py
  head.py -n +40 head.py  # akin to vim +40 head.py
"""


import sys

import argdoc


def main():
    args = argdoc.parse_args()
    sys.stderr.write("{}\n".format(args))
    sys.stderr.write("{}\n".format(argdoc.format_usage().rstrip()))
    sys.stderr.write("head.py: error: not implemented\n")
    sys.exit(2)  # exit 2 from rejecting usage


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
