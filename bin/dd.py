#!/usr/bin/env python3

r"""
usage: dd.py [-h]

copy from input stream to output stream

optional arguments:
  -h, --help  show this help message and exit

quirks:
  does forward interactive input lines immediately, unlike bash
  crashes "pybashish" shell if called from there, at ⌃C SIGINT
  pressing ⌃T at mac works, pressing ⌃T at linux doesn't
  kill with SIGUSR1 works at linux (TODO: write example of this & also test Mac)

unsurprising quirks:
  does prompt once for stdin, like bash "grep -R", unlike bash "dd"
  accepts only the "stty -a" line-editing c0-control's, not the "bind -p" c0-control's

examples:
  dd  # run demo of ⌃T SIGINFO and ⌃C SIGINT, till ⌃D EOF or ⌃\ SIGQUIT
"""
# FIXME: fix "dd" quirks


from __future__ import print_function

import contextlib
import signal
import sys

import argdoc


def main():

    argdoc.parse_args()

    # Print banner  # in place of popular def prompt_tty_stdin

    stderr_print()
    stderr_print(
        "dd.py: Press ⌃T SIGINFO to see progress, a la Linux:  killall -SIGUSR1 python3"
    )
    stderr_print("dd.py: Press ⌃Z to pause, and then tell Bash to 'fg' to resume")
    stderr_print(
        r"dd.py: Press ⌃C SIGINT to quit, press ⌃\ SIGQUIT if you really mean it"
    )
    stderr_print("Press ⌃D EOF to quit")
    stderr_print()

    # Define SIGINFO

    def siginfo(signum, frame):
        stderr_print("dd.py: ⌃T SIGINFO")

    with SigInfoHandler(handler=siginfo):

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


#
# Define some Python idioms
#


# deffed in many files  # missing from docs.python.org
class SigInfoHandler(contextlib.ContextDecorator):
    """Assign to global "signal.signal(signal.SIGINFO)" at entry, restore at exit"""

    def __init__(self, handler):
        self.handler = handler

    def __enter__(self):
        handler = self.handler
        if hasattr(signal, "SIGINFO"):  # Mac
            with_siginfo = signal.signal(signal.SIGINFO, handler)
        else:  # Linux
            with_siginfo = signal.signal(signal.SIGUSR1, handler)
        self.with_siginfo = with_siginfo
        return self

    def __exit__(self, *exc_info):
        with_siginfo = self.with_siginfo
        if hasattr(signal, "SIGINFO"):  # Mac
            signal.signal(signal.SIGINFO, with_siginfo)
        else:  # Linux
            signal.signal(signal.SIGUSR1, with_siginfo)


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
