#!/usr/bin/env python3

r"""
usage: sponge.py [-h] [-a] [FILE [FILE ...]]

read every line of input bytes (or chars), then write a copy to each output

positional arguments:
  FILE          file to write (default: stdout)

optional arguments:
  -h, --help    show this help message and exit
  -a, --append  append to each file, rather than replacing each file

bugs:
  writes more than one output, unlike classic "moreutils" "sponge"
  accepts "--a", "--ap", "--app", ... "--append" in place of classic "-a"
  doesn't preserve the permissions of replaced output files
  never renames a temporary file to replace the output file more indivisibly
  doesn't first write a copy to a temporary file
  fails if more input than free memory

unsurprising bugs:
  does prompt once for stdin, like bash "grep -R", unlike bash "cat" and "cat -"
  accepts only the "stty -a" line-editing c0-control's, not the "bind -p" c0-control's

examples:
  echo one >t.txt && cat t.txt
  echo two | sponge.py t.txt && cat t.txt
  cat t.txt | sponge.py t.txt && cat t.txt
  echo three | sponge.py -a t.txt && cat t.txt
"""


import contextlib
import os
import sys

import argdoc


def main(argv):

    args = argdoc.parse_args(argv[1:])

    paths = args.files if args.files else ["-"]

    # Catenate each binary (or text) file

    prompt_tty_stdin()

    with open("/dev/stdin", "rb") as incoming:
        sponge = incoming.read()

    for path in paths:
        writable = "/dev/stdout" if (path == "-") else path
        try:
            awb_mode = "ab" if args.append else "wb"
            with open(writable, awb_mode) as outgoing:
                os.write(outgoing.fileno(), sponge)
        except FileNotFoundError as exc:
            stderr_print("sponge.py: error: {}: {}".format(type(exc).__name__, exc))
            sys.exit(1)


#
# Git-track some Python idioms here
#


# deffed in many files  # missing from docs.python.org
def prompt_tty_stdin():
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


# deffed in many files  # missing from docs.python.org
class BrokenPipeErrorSink(contextlib.ContextDecorator):
    """Cut unhandled BrokenPipeError down to sys.exit(1)

    Test with large Stdout cut sharply, such as:  find.py ~ | head

    More narrowly than:  signal.signal(signal.SIGPIPE, handler=signal.SIG_DFL)
    As per https://docs.python.org/3/library/signal.html#note-on-sigpipe
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
    sys.exit(main(sys.argv))  # FIXME
    with BrokenPipeErrorSink():
        sys.exit(main(sys.argv))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
