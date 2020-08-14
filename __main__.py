#!/usr/bin/env python3

from __future__ import print_function

import os
import subprocess
import sys

import bin.argdoc  # FIXME: packaging  # concisely require Python >= June/2019 Python 3.7

bin.argdoc.require_sys_version_info()  # duck foolish Flake8 F401 "'...' imported but unused"


def main(argv):
    """
    Run "bin/bash.py"
    """

    # Add the colocated "bin/" dir, as a dir of importable packages

    file_dir = os.path.split(os.path.realpath(__file__))[0]
    bin_dir = os.path.join(file_dir, "bin")

    # Call Bash Py

    bin_bash_py = os.path.join(bin_dir, "bash.py")
    ran = subprocess.run([bin_bash_py] + ["-i"] + argv[1:])
    sys.exit(ran.returncode)


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
