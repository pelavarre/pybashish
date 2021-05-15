#!/usr/bin/env python3

"""
usage: wc.py [-h] [-L] [-l] [-m] [-c] [FILE [FILE ...]]

count lines and words and characters and bytes

positional arguments:
  FILE                  a file to examine (default: stdin)

optional arguments:
  -h, --help            show this help message and exit
  -L, --max-line-length
                        count max characters per line
  -l, --lines           count lines
  -m, --chars           count characters
  -c, --bytes           count bytes

quirks:
  acts like "wc -L -l" if called without args, unlike Bash "wc"

unsurprising quirks:
  prompts for stdin, like mac bash "grep -R .", unlike bash "wc"
  accepts the "stty -a" line-editing c0-control's, not also the "bind -p" c0-control's
  takes "-" as meaning "/dev/stdin", like linux "wc -", unlike mac "wc -"

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
