#!/usr/bin/env python3

"""
usage: tail.py [-h] [-F] [-f] [--retry] [-n COUNT] [FILE [FILE ...]]

show just the trailing lines of a file

positional arguments:
  FILE                  the file to drop leading lines from (default: stdin)

optional arguments:
  -h, --help            show this help message and exit
  -F                    --follow --retry
  -f, --follow          don't quit, keep the file open, to show the lines appended to it, if any
  --retry               close and reopen the file, when the file is renamed or rotated
  -n COUNT, --lines COUNT
                        how many trailing lines to show (default: 10)

quirks:
  takes a count led by "+" as how many leading lines to drop
  takes "-5" or "+9" and such, like mac "tail", unlike linux "tail -n"

unsurprising quirks:
  prompts for stdin, like mac bash "grep -R .", unlike bash "tail"
  accepts the "stty -a" line-editing c0-control's, not also the "bind -p" c0-control's
  takes "-" as meaning "/dev/stdin", like linux "tail -", unlike mac "tail -"

examples:
  tail.py /dev/null
  tail.py tail.py
  tail.py -5 tail.py
  tail.py -n 5 tail.py
  python3 -c 'import this' |tail.py -n 3 |cat.py -n
"""


import sys

import argdoc


def main():
    args = argdoc.parse_args()
    sys.stderr.write("{}\n".format(args))
    sys.stderr.write("{}\n".format(argdoc.format_usage().rstrip()))
    sys.stderr.write("tail.py: error: not implemented\n")
    sys.exit(2)  # exit 2 from rejecting usage


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
