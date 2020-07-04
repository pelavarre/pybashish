#!/usr/bin/env python3

"""
usage: cat.py [-h] [-n] [FILE [FILE ...]]

copy files to standard output ("cat"enate them)

positional arguments:
  FILE          a file to copy

optional arguments:
  -h, --help    show this help message and exit
  -n, --number  number each line of output

bugs:
  doesn't forward interactive input lines immediately, unlike Bash
  doesn't define "cat -etv" to show all "us-ascii" rejects
  doesn't undo Mac "use smart quotes and dashes"
  doesn't convert indented line-broken plain-text to Html
"""
# FIXME FIXME: fix "cat" bugs: interactive, -etv, smart quotes and dashes, Html

from __future__ import print_function

import contextlib
import os
import sys

import argdoc


def main(argv):

    args = argdoc.parse_args(argv[1:])
    relpaths = args.files if args.files else ["-"]

    if "-" in relpaths:
        stderr_print("Press ⌃D EOF to quit")
        stderr_print("bug: doesn't forward interactive input lines immediately")

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
                stderr_print("{}: {}".format(type(exc).__name__, exc))
                sys.exit(1)

        # Number on the right side of 6 columns, then a hard tab 2 column separator, then the line

        if args.number:

            with open(relpath, "r") as reading:
                for (
                    line
                ) in reading.readlines():  # FIXME: stop implying buffers of whole files
                    print("{:6}\t{}".format(line_index, line.rstrip()))
                    line_index += 1

            continue

        # Copy binary out without numbering the lines

        with open(relpath, "rb") as reading:
            fileno = sys.stdout.fileno()
            os.write(
                fileno, reading.read()
            )  # FIXME: stop asking for buffers of whole files


def stderr_print(*args):
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
