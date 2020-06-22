#!/usr/bin/env python3

import contextlib
import signal
import sys


def main():

    stderr_print()
    stderr_print(
        "dd.py: Press ⌃T SIGINFO to see progress, a la Linux 'killall -i -10 dd # SIGUSR1'"
    )
    stderr_print("dd.py: Press ⌃Z to pause, and then tell Bash to 'fg' to resume")
    stderr_print(
        r"dd.py: Press ⌃C SIGINT to quit, press ⌃\ SIGQUIT if you really mean it"
    )
    stderr_print()

    def siginfo(signum, frame):
        stderr_print("dd.py: ⌃T SIGINFO")

    with SigInfoHandler(siginfo):

        drop_sigint_once = True
        while True:

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

            if not line:
                stderr_print("dd.py: ⌃D EOF")
                break

            print(line.rstrip())


class SigInfoHandler(contextlib.ContextDecorator):
    def __init__(self, handle_signum_frame):
        self.handle_signum_frame = handle_signum_frame

    def __enter__(self):
        handle_signum_frame = self.handle_signum_frame
        with_siginfo = signal.signal(signal.SIGINFO, handle_signum_frame)
        self.with_siginfo = with_siginfo
        return self

    def __exit__(self, *exc):
        with_siginfo = self.with_siginfo
        signal.signal(signal.SIGINFO, with_siginfo)


def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main()


# pulled from:  git clone https://github.com/pelavarre/pybashish.git
