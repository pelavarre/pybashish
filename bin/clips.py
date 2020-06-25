#!/usr/bin/env python3

r"""
usage: clips.py [-h] [REGEX [REGEX ...]]

search out some texts clipped from wherever

positional arguments:
  REGEX         a regex to match

optional arguments:
  -h, --help  show this help message and exit
"""

from __future__ import print_function

import contextlib
import os
import sys

import argdoc  # FIXME: packaging


def main(argv):

    args = argdoc.parse_args()

    print(args)  # FIXME: do good stuff


def stderr_print(*args):
    print(*args, file=sys.stderr)


class BashPipeable(contextlib.ContextDecorator):
    """Silence any unhandled BrokenPipeError down to nothing but sys.exit(1)

    Yes, this is try-except-pass, but it is significantly more narrow than:
        signal.signal(signal.SIGPIPE, handler=signal.SIG_DFL)

    See https://docs.python.org/3/library/signal.html#note-on-sigpipe
    """

    def __enter__(self):

        return self

    def __exit__(self, *exc_info):

        (exc_type, exc_value, exc_traceback,) = exc_info
        if isinstance(exc_value, BrokenPipeError):
            null_fileno = os.open(os.devnull, os.O_WRONLY)
            os.dup2(null_fileno, sys.stdout.fileno())
            # FIXME: add test to reliably and quickly demo needing to "dup2" the "stdout.fileno"
            sys.exit(1)


if __name__ == "__main__":
    sys.exit(main(sys.argv))


# pulled from:  git clone https://github.com/pelavarre/pybashish.git
