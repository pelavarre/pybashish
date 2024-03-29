#!/usr/bin/env python3

"""
usage:  python3 ../pybashish/
"""

from __future__ import print_function

import argparse
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
    handler = signal.SIG_IGN  # no KwArgs for 'signal.signal' till later Python
    with_handler = signal.signal(signal.SIGINT, handler)
    try:
        ran = subprocess_run([bin_bash_py] + ["-i"] + argv[1:])
    finally:
        signal.signal(signal.SIGINT, with_handler)
    sys.exit(ran.returncode)


# deffed in many files  # since Sep/2015 Python 3.5
def subprocess_run(args, **kwargs):
    """
    Emulate Python 3 "subprocess.run"

    Don't help the caller remember to encode empty Stdin as:  stdin=subprocess.PIPE
    """

    # Trust the library, if available

    if hasattr(subprocess, "run"):
        run = subprocess.run(args, **kwargs)  # pylint: disable=subprocess-run-check

        return run

    # Convert KwArgs to Python 2

    kwargs2 = dict(kwargs)  # args, cwd, stdin, stdout, stderr, shell, ...

    for kw in "encoding errors text universal_newlines".split():
        if kw in kwargs:
            raise NotImplementedError("keyword {}".format(kw))

    for kw in "check input".split():
        if kw in kwargs:
            del kwargs2[kw]  # drop now, catch later

    input2 = None
    if "input" in kwargs:
        input2 = kwargs["input"]

        if "stdin" in kwargs:
            raise ValueError("stdin and input arguments may not both be used.")

        assert "stdin" not in kwargs2
        kwargs2["stdin"] = subprocess.PIPE

    # Emulate the library roughly, because often good enough

    sub = subprocess.Popen(args, **kwargs2)  # pylint: disable=consider-using-with
    (stdout, stderr) = sub.communicate(input=input2)
    returncode = sub.poll()

    if "check" in kwargs:
        if returncode != 0:

            raise subprocess.CalledProcessError(
                returncode=returncode, cmd=args, output=stdout
            )

    # Succeed

    run = argparse.Namespace(
        args=args, stdout=stdout, stderr=stderr, returncode=returncode
    )

    return run


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
