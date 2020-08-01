#!/usr/bin/env python3

r"""
usage: cat.py [-h] [-n] [FILE [FILE ...]]

copy files to standard output ("cat"enate them)

positional arguments:
  FILE          a file to copy out

optional arguments:
  -h, --help    show this help message and exit
  -n, --number  number each line of output

bugs:
  does prompt once for Stdin, when Stdin chosen as FILE "-" or by no FILE args, unlike Bash "cat"
  doesn't accurately catenate binary files, unlike Bash
  does convert classic Mac CR "\r" end-of-line to Linux LF "\n", unlike Bash "cat"
  does always end the last line with Linux LF "\n" end-of-line, unlike Bash "cat"
  does print hard b"\x09" after each line number, via "{:6}\t", same as Bash "cat"
  accepts only the "stty -a" line-editing C0-Control's, not the "bind -p" C0-Control's
  doesn't define "cat -etv" to show all "us-ascii" rejects
  doesn't undo Mac "use smart quotes and dashes"
  doesn't convert indented line-broken plain-text to Html

examples:
  cat -  # copy out each line of input
  cat - >/dev/null  # echo and discard each line of input
  pbpaste | cat -etv
"""
# FIXME FIXME: fix "cat" bugs: -etv, smart quotes and dashes, Html
# FIXME: dream up a good way to accurately catenate binary files

from __future__ import print_function

import contextlib
import os
import sys

import argdoc


def main(argv):

    args = argdoc.parse_args(argv[1:])
    relpaths = args.files if args.files else ["-"]

    if "-" in relpaths:
        prompt_tty_stdin()

    # Visit each file

    line_index = 1
    for relpath in relpaths:  # FIXME: evade Linux-specific "/dev/stdin"
        relpath = "/dev/stdin" if (relpath == "-") else relpath

        # Fail fast if file not found

        if not os.path.exists(relpath):  # FIXME: stop branching on os.path.exists
            try:
                with open(relpath, "rt"):
                    pass
            except FileNotFoundError as exc:
                stderr_print("cat.py: error: {}: {}".format(type(exc).__name__, exc))
                sys.exit(1)

        # Number on the right side of 6 columns, then a hard tab 2 column separator, then the line

        with open(relpath, "r") as reading:

            line = "\n"
            while True:

                line = reading.readline()
                if not line:
                    break

                rstripped = line.rstrip()

                if args.number:
                    print("{:6}\t{}".format(line_index, rstripped))
                else:
                    print(rstripped)

                line_index += 1


def prompt_tty_stdin():  # deffed in many files
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


def stderr_print(*args):  # deffed in many files
    print(*args, file=sys.stderr)


class BrokenPipeSink(contextlib.ContextDecorator):
    """Silence any unhandled BrokenPipeError down to nothing but sys.exit(1)

    Yes, this is try-except-pass, but it is significantly more narrow than:

        signal.signal(signal.SIGPIPE, handler=signal.SIG_DFL)

    Test with lots of slow Stdout suddenly cut short, such as

        bin/cat.py -n bin/*.py | head

        bin/find.py ~ | head

    See https://docs.python.org/3/library/signal.html#note-on-sigpipe
    """

    def __enter__(self):

        return self

    def __exit__(self, *exc_info):

        (exc_type, exc, exc_traceback,) = exc_info
        if isinstance(exc, BrokenPipeError):  # catch this one

            null_fileno = os.open(os.devnull, os.O_WRONLY)
            os.dup2(null_fileno, sys.stdout.fileno())  # avoid the next one

            sys.exit(1)


if __name__ == "__main__":
    with BrokenPipeSink():
        sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
