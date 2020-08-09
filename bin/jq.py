#!/usr/bin/env python3

"""
usage: jq.py [-h] FILTER [FILE [FILE ...]]

walk the json at standard input

positional arguments:
  FILTER      filter coded as jq
  FILE        a file of data coded as json, such as "/dev/stdin"

optional arguments:
  -h, --help  show this help message and exit

bugs:
  give the available precision, don't floor to the last second like Bash

examples:
  echo '["aa", "cc", "bb"]' | jq .
  jq . <(echo '["aa", "cc", "bb"]')
"""

import json
import sys

import argdoc


def main():
    args = argdoc.parse_args()

    # Fetch

    files = args.files if args.files else "-".split()
    for file_ in files:

        if file_ in ("-", "/dev/stdin",):
            prompt_tty_stdin()
            chars = sys.stdin.read()
        else:
            with open(file_) as incoming:
                chars = incoming.read()

        # Munge

        bits = json.loads(chars)
        stdout = json.dumps(bits) + "\n"

        # Store

        sys.stdout.write(stdout)


# deffed in many files  # missing from docs.python.org
def prompt_tty_stdin():
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
