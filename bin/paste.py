#!/usr/bin/env python3

"""
usage: paste.py [-h] [FILE [FILE ...]]

copy each file into place as a column

positional arguments:
  FILE        a file to copy (default: stdin)

optional arguments:
  -h, --help  show this help message and exit

quirks:
  no implementation

unsurprising quirks:
  prompts for stdin, like mac bash "grep -R .", unlike bash "paste -"
  accepts the "stty -a" line-editing c0-control's, not also the "bind -p" c0-control's
  takes no args as meaning file stdin, like linux "paste", unlike mac "paste"

examples:
  Oh no! No examples disclosed!! 💥 💔 💥
"""

# FIXME: left-justify, right-justify, center, with and without sponging
# FIXME: options to add column names and separators
# FIXME: options to take column names as a first row or as a column


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
