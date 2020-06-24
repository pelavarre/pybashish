#!/usr/bin/env python3

r"""
usage: help.py [-h]

print some help

optional arguments:
  -h, --help  show this help message and exit
"""


import glob
import os
import sys

import argdoc


def main():

    argdoc.parse_args()

    file_dir = os.path.split(os.path.realpath(__file__))[0]
    os.chdir(file_dir)

    globbed = glob.glob("*.py")

    verbs = list()
    for what in globbed:
        name = os.path.splitext(what)[0]
        if not name.startswith("_"):
            verb = name.strip("_")
            verbs.append(verb)

    stderr_print()
    stderr_print("For more information, try one of these:")
    stderr_print()

    for verb in sorted(verbs):
        print("{} --help".format(verb))

    stderr_print()


def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main()


# pulled from:  git clone https://github.com/pelavarre/pybashish.git
