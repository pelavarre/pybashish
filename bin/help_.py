#!/usr/bin/env python3

r"""
usage: help_.py [-h] [VERB]

print some help

positional arguments:
  VERB        a verb to explain

optional arguments:
  -h, --help  show this help message and exit

examples:
  help_.py
  help_.py fmt
  man bash
  man zshall
"""

from __future__ import print_function

import glob
import os
import shlex
import stat
import subprocess
import sys

import argdoc


def main():

    args = argdoc.parse_args()

    #

    file_dir = os.path.split(os.path.realpath(__file__))[0]

    os.chdir(file_dir)
    globbed = glob.glob("*.py")

    executable_whats = list()
    for what in globbed:
        stats = os.stat(what)
        if stats.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            executable_whats.append(what)

    whats_by_verb = dict()
    for what in executable_whats:
        name = os.path.splitext(what)[0]
        if not name.startswith("_"):
            verb = name.strip("_")

            whats_by_verb[verb] = what

    #

    if args.verb:
        what = whats_by_verb[args.verb]
        shline = "./{} --help".format(what)
        ran = subprocess.run(shlex.split(shline))
        sys.exit(ran.returncode)

    #

    stderr_print()
    stderr_print("For more information, try one of these:")
    stderr_print()
    sys.stderr.flush()

    verbs = list(whats_by_verb.keys())
    verbs.append("history")  # FIXME: collect all the BUILTINS of "bin/bash.py"

    for verb in sorted(verbs):
        shline = "{} --help".format(verb)
        print(shline)
    sys.stdout.flush()

    stderr_print()


# deffed in many files  # missing from docs.python.org
def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
