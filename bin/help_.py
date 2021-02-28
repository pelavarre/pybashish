#!/usr/bin/env python3

r"""
usage: help_.py [-h] [VERB]

print some help

positional arguments:
  VERB        a verb to explain, such as "grep" or "echo"

optional arguments:
  -h, --help  show this help message and exit

examples:
  help_.py
  help_.py fmt  # calls out to:  fmt.py --help
  man bash
  man zshall
"""
# FIXME: help '#', help :, help .., help -


from __future__ import print_function

import glob
import os
import shlex
import stat
import subprocess
import sys
import textwrap

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
    stderr_print(
        textwrap.dedent(
            """
            Python apps should introduce themselves well

            Try typing the name of the app, and adding " --help" or " -h"

            For instance:

                echo --h
                grep -h | head
            """
        ).strip()
    )
    stderr_print()
    stderr_print("Next try one of:")
    stderr_print()

    #

    verbs = list(whats_by_verb.keys())
    verbs.append("-")
    verbs.append("..")
    # verbs.append(":")  # FIXME: think more about shline=": --help"
    verbs.append("history")  # FIXME: collect all the BUILTINS of "bash.py"
    verbs.sort()

    print_cells(verbs, width=89)  # 89 columns is a 2020 Black terminal

    stderr_print()
    stderr_print('Note: The "#" hash mark means ignore the following chars in the line')
    stderr_print(
        'Note: The ":" colon as the first word means mostly ignore the following words in the line'
    )

    stderr_print()


#
# Define some Python idioms
#


# deffed in many files  # missing from docs.python.org
def print_cells(cells, dent="    ", sep="  ", width=None):
    """
    Print cells to fit inside a terminal width

    See also: textwrap.fill break_on_hyphens=False break_long_words=False
    """

    dent = "    "
    sep = "  "

    joined = None
    for cell in cells:
        if not joined:
            joined = dent + cell
        else:

            printable = joined
            joined = "{}{}{}".format(joined, sep, cell)

            if len(joined) >= width:
                print(printable)
                joined = dent + cell

    if joined:
        print(joined)


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
