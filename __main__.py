#!/usr/bin/env python3

from __future__ import print_function

import os
import sys
import subprocess


def main(argv):
    """
    Run "bin/bash.py"
    """

    # Reject Python 2 concisely

    require_sys_version_info(3, 7)

    # Add the colocated "bin/" dir, as a dir of importable packages

    file_dir = os.path.split(os.path.realpath(__file__))[0]
    bin_dir = os.path.join(file_dir, "bin")

    # Call Bash Py

    bin_bash_py = os.path.join(bin_dir, "bash.py")
    ran = subprocess.run([bin_bash_py] + argv[1:])
    sys.exit(ran.returncode)


def require_sys_version_info(*min_info):

    str_min_info = ".".join(str(i) for i in min_info)
    str_sys_info = "/ ".join(sys.version.splitlines())

    if sys.version_info < min_info:

        stderr_print()
        stderr_print("This is Python {}".format(str_sys_info))
        stderr_print()
        stderr_print("Please try Python {} or newer".format(str_min_info))
        stderr_print()

        sys.exit(1)


def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv)


# pulled from:  git clone https://github.com/pelavarre/pybashish.git
