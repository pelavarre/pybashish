#!/usr/bin/env python3

r"""
usage: xargs.py [-h] [-n MAX_ARGS]

split and rejoin the words of all lines of input into one line of output

options:
  -h, --help            show this help message and exit
  -n MAX_ARGS, --max-args MAX_ARGS
                        words per line

examples:
  echo 'a  b  c$  d  e$$f  g$' |tr '$' '\n' |xargs.py  # join words of lines into one line
  echo a b c d e f g |xargs.py -n 1  # split words of lines into one word per line
  expand.py |xargs.py -n 1  # convert &nbsp; to spaces, etc, before trying to split it
"""


import sys

import argdoc


def main():
    """Run from the command line"""

    args = argdoc.parse_args()

    stdin = sys.stdin.read()

    words = stdin.split()
    len_words = len(words)
    words_per_line = len_words if (args.n is None) else int(args.n)

    if len_words:
        for index in range(0, len_words, words_per_line):

            argv_tail = words[index:][:words_per_line]

            stdout = "{}\n".format(" ".join(argv_tail))
            sys.stdout.write(stdout)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
