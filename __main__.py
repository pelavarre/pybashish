#!/usr/bin/env python3

from __future__ import print_function

import os
import signal
import subprocess
import sys


def main(argv):
    """
    Run "bin/bash.py"
    """

    # Add the colocated "bin/" dir, as a dir of importable packages

    file_dir = os.path.split(os.path.realpath(__file__))[0]
    bin_dir = os.path.join(file_dir, "bin")

    # Call Bash Py, except don't take SIGINT KeyboardInterrupt's from it

    bin_bash_py = os.path.join(bin_dir, "bash.py")
    with_siginfo = signal.signal(signal.SIGINT, handler=signal.SIG_IGN)
    try:
        ran = subprocess.run([bin_bash_py] + ["-i"] + argv[1:])
    finally:
        signal.signal(signal.SIGINT, with_siginfo)
    sys.exit(ran.returncode)


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
