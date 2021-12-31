#!/usr/bin/env python3

"""
usage: wc.py [-h] [-l] [-w] [-m] [-c] [-L] [FILE ...]

count lines and words and characters and bytes

positional arguments:
  FILE                  a file to examine (default: stdin)

options:
  -h, --help            show this help message and exit
  -l, --lines           count lines
  -w, --words           count lines
  -m, --chars           count characters
  -c, --bytes           count bytes
  -L, --max-line-length
                        count max characters per line

quirks:
  acts like 'wc -l' if called without args, unlike Bash 'wc' and 'wc -lwc'

unsurprising quirks:
  prompts Tty Stdin, like Mac 'grep -R .', unlike Bash 'wc'
  takes 'stty -a' line-editing C0-Control's, not also 'bind -p' C0-Control's
  takes '-' as meaning '/dev/stdin', like Linux 'wc -', unlike Mac 'wc -'
  takes '--help' as an option, like Linux 'wc --help', unlike Mac 'wc --help'

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
