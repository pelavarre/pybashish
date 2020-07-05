#!/usr/bin/env python3

r"""
usage: dd.py [-h]

copy from input stream to output stream

optional arguments:
  -h, --help  show this help message and exit

bugs:
  does forward interactive input lines immediately, unlike Bash
  crashes "pybashish" shell if called from there, at ⌃C SIGINT

examples:
  dd  # run demo of ⌃T SIGINFO and ⌃C SIGINT, till ⌃D EOF or ⌃\ SIGQUIT
"""
# FIXME: fix more bugs

from __future__ import print_function

import contextlib
import signal
import sys

import argdoc


def main():

    argdoc.parse_args()

    # Print banner

    stderr_print()
    stderr_print(
        "dd.py: Press ⌃T SIGINFO to see progress, a la Linux 'killall -i -10 dd # SIGUSR1'"
    )
    stderr_print("dd.py: Press ⌃Z to pause, and then tell Bash to 'fg' to resume")
    stderr_print(
        r"dd.py: Press ⌃C SIGINT to quit, press ⌃\ SIGQUIT if you really mean it"
    )
    stderr_print("bug: does forward interactive input lines immediately")
    stderr_print()

    # Define SIGINFO

    def siginfo(signum, frame):
        stderr_print("dd.py: ⌃T SIGINFO")

    with SigInfoHandler(siginfo):

        # Serve till EOF or SIGINT

        drop_sigint_once = True
        while True:

            # Pull one line

            try:
                line = sys.stdin.readline()
            except KeyboardInterrupt:

                if not drop_sigint_once:
                    stderr_print()
                    break
                drop_sigint_once = False

                stderr_print(
                    "dd.py: KeyboardInterrupt: Thank you for SIGINT, press it again if you mean it"
                )

                continue  # FIXME: ⌃C SIGINT inside "dd.py" inside "bash.py" chokes

            drop_sigint_once = True

            # Exit at end-of-file

            if not line:
                stderr_print("dd.py: ⌃D EOF")
                break

            print(line.rstrip())  # FIXME: call for larger buffer inside "dd"


class SigInfoHandler(contextlib.ContextDecorator):
    """Back up and redefined global SIGINFO at entry, restore at exit"""

    def __init__(self, handle_signum_frame):
        self.handle_signum_frame = handle_signum_frame

    def __enter__(self):
        handle_signum_frame = self.handle_signum_frame
        with_siginfo = signal.signal(signal.SIGINFO, handle_signum_frame)
        self.with_siginfo = with_siginfo
        return self

    def __exit__(self, *exc_info):
        with_siginfo = self.with_siginfo
        signal.signal(signal.SIGINFO, with_siginfo)


def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
