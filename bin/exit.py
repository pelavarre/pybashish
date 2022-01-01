#!/usr/bin/env python3

"""
usage: exit.py [-h] [STATUS]

inject a choice of process returncode

positional arguments:
  STATUS      an eight-bit code seen as happy if zero, sad if positive, very sad if negative

options:
  -h, --help  show this help message and exit

quirks:
  complains to stderr of codes outside -128..127
  returns codes 0..255 (in particular, substitutes 128..255 for -128..-1)

examples:
  exit
  exit 0  # happy 😊
  exit 1  # sad 😢
  exit -1  # very sad 😠
"""


import sys

import argdoc


def main():
    args = argdoc.parse_args()

    if args.status is None:
        sys.exit()

    status = int(args.status)

    if not (-0x80 <= status <= 0x7F):
        partial = status & 0xFF
        sys.stderr.write("exit.py: error: returning {} as {}\n".format(status, partial))

    sys.exit(status)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
