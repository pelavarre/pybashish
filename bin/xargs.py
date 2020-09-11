#!/usr/bin/env python3

r"""
usage: xargs.py [-h] [-n MAX_ARGS]

split and rejoin the words of all lines of input into one line of output

optional arguments:
  -h, --help            show this help message and exit
  -n MAX_ARGS, --max-args MAX_ARGS
                        words per line

examples:
  echo 'a  b  c$  d  e$$f  g$' | tr '$' '\n' | xargs.py  # join words of lines into one line
  echo a b c d e f g | xargs.py -n 1  # split words of lines into one word per line
"""

_ = """  # FIXME: say/code something about sed 's,  *, ,g' rejoin of split words

(black) % cat a | tail -n +3 | xargs -n 5
2020-08-22 | 19669 | 34606
2020-08-23 | 19752 | 36006
2020-08-24 | 19576 | 36185
2020-08-25 | 18057 | 27863
2020-08-26 | 17139 | 24816
2020-08-27 | 17533 | 26120
2020-08-28 | 19157 | 31485
2020-08-29 | 19749 | 33650
(black) %


"""


import sys

import argdoc


def main():
    """Run from the command line"""

    args = argdoc.parse_args()

    stdin = sys.stdin.read()
    words = stdin.split()
    len_words = len(words)
    words_per_line = len_words if (args.max_args is None) else int(args.max_args)

    if len_words:
        for index in range(0, len_words, words_per_line):
            argv_tail = words[index:][:words_per_line]
            stdout = "{}\n".format(" ".join(argv_tail))
            sys.stdout.write(stdout)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
