#!/usr/bin/env python3

"""
usage: watch.py [-h] [-n SECS] [WORD ...]

repeat a Bash command every so often till Control+C, and delete duplicate outputs

positional arguments:
  WORD                  word of command

options:
  -h, --help            show this help message and exit
  -n SECS, --interval SECS
                        seconds to wait between updates (default: 0.2s)

quirks:
  doesn't default to the 2s intervals of the 1970s

examples:
  watch.py
  watch.py -h
  watch.py  df -h
  watch.py -n 0.100  df -h
  watch.py -n 0.100 --  df -h

see also:  man script, man watch
"""

# FIXME: demo watching:  pbpaste.py |cat.py -v


from __future__ import print_function

import datetime
import sys
import time

import argdoc


def main(argv):
    """Run from the command line"""

    args = argdoc.parse_args(argv[1:])
    main.args = args

    stderr_print(args)
    stderr_print(argdoc.format_usage().rstrip())
    stderr_print("watch.py: error: not implemented")
    sys.exit(2)  # exit 2 from rejecting usage

    main.era = datetime.datetime.now()

    last_result = None
    next_call = main.era
    while True:

        when_called = datetime.datetime.now()
        result = check_transcript(args.words)
        when_returned = datetime.datetime.now()

        if result != last_result:
            last_result = result

            sys.stdout.write("\x1B[H\x1B[2J")  # Ansi Clear from $(clear |cat -tv)
            sys.stdout.write("\n")  # end the line to keep the 'screen' text 'grep'pable

            (exit_status, out_bytes) = result

            print(
                "{} + N * {}".format(
                    when_called, datetime.timedelta(seconds=args.interval)
                )
            )
            print()
            print("+ {}".format(shlex_join(args.words)))
            sys.stdout.write(out_bytes)
            print("+ exit {}".format(exit_status))
            print()
            print("{} - {}".format(when_returned, (when_returned - when_called)))

            sys.stdout.flush()

        while next_call < datetime.datetime.now():
            next_call += datetime.timedelta(seconds=args.interval)
        next_call += datetime.timedelta(seconds=args.interval)

        sleepy = (next_call - datetime.datetime.now()).total_seconds()
        assert sleepy > 0
        time.sleep(sleepy)


def check_transcript(shline):
    raise NotImplementedError()


def shlex_join(argv):
    raise NotImplementedError()


#
# Define some Python idioms
#


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    """Print the Args, but to Stderr, not to Stdout"""

    sys.stdout.flush()
    print(*args, file=sys.stderr)
    sys.stderr.flush()  # like for kwargs["end"] != "\n"


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
