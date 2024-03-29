#!/usr/bin/env python3

r"""
usage: help.py [-h] [VERB]

print some help

positional arguments:
  VERB        a verb to explain, such as "grep" or "echo"

options:
  -h, --help  show this help message and exit

examples:
  help.py
  help.py fmt  # calls out to:  fmt.py --help
  man bash
  man zshall
"""
# FIXME: help '#', help :, help .., help -


from __future__ import print_function

import argparse
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

            assert verb not in whats_by_verb
            whats_by_verb[verb] = what

    #

    if args.verb:
        what = whats_by_verb[args.verb]
        shline = "./{} --help".format(what)
        ran = subprocess_run(shlex.split(shline))
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
                grep -h |head
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
def stderr_print(*args):
    """Print the Args, but to Stderr, not to Stdout"""

    sys.stdout.flush()
    print(*args, file=sys.stderr)
    sys.stderr.flush()  # like for kwargs["end"] != "\n"


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
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
