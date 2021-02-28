#!/usr/bin/env python3

"""
usage: pwd_.py [-h] [-P] [--brief] [--home]

show the os.environ["PWD"], by default just its "os.path.abspath"

optional arguments:
  -h, --help      show this help message and exit
  -P, --physical  show the "realpath"s, not "abspath"s, of sym links
  --brief         show the briefest abspath/ homepath/ realpath
  --home          show the ~/... relpath in place of abspath or realpath

quirks:
  defaults to "--home", in the spirit of Bash "dirs +0" and Zsh "dirs -p", unlike their "pwd"s
  offers "--brief" and "--home", unlike Bash anywhere
  offers "--physical" like Linux, not just "-P" like Mac
  doesn't offer the explicit "--logical" of Linux, nor the "-L" of Mac and Linux

examples:
  pwd
  pwd -P
  pwd_.py --brief
  pwd_.py --home
"""
# FIXME: add "--verbose" a la "hostname"
# FIXME: somehow remember we don't want to abbreviate down to colliding "-" the unconventional "--"


from __future__ import print_function

import os
import sys

import argdoc


def main(argv):

    pwd_argv_tail = argv[1:] if argv[1:] else ["--home"]  # FIXME: more robust default
    args = argdoc.parse_args(pwd_argv_tail)

    pwd = os.environ["PWD"]
    abspath = os.path.abspath(pwd)
    realpath = os.path.realpath(pwd)

    try:
        gotcwd = os.getcwd()
    except FileNotFoundError as exc:
        print(pwd)
        stderr_print("pwd.py: error: {}: {}".format(type(exc).__name__, exc))
        sys.exit(1)  # FIXME: more robust "pwd" vs the current working dir deleted

    assert gotcwd == realpath

    path = realpath if args.physical else abspath  # FIXME: count -L -P contradictions
    formatter = min_path_formatter_not_relpath(path)
    briefpath = formatter(path)
    homepath = os_path_homepath(path)

    printable = path
    if args.home:
        printable = homepath
    elif args.brief:  # FIXME: count -H -B contradictions
        printable = briefpath

    print(printable)


#
# Define some Python idioms
#


# deffed in many files  # missing from docs.python.org
def os_path_homepath(path):
    """Return the ~/... relpath of a file or dir inside the Home, else the realpath"""

    home = os.path.realpath(os.environ["HOME"])

    homepath = path
    if path == home:
        homepath = "~"
    elif path.startswith(home + os.path.sep):
        homepath = "~" + os.path.sep + os.path.relpath(path, start=home)

    return homepath


# deffed in many files  # missing from docs.python.org
def min_path_formatter_not_relpath(exemplar):
    """Choose the def that abbreviates this path most sharply: abs, real, rel, or home"""

    formatters = (
        os.path.abspath,
        os.path.realpath,
        # os.path.relpath,
        os_path_homepath,
    )

    formatter = formatters[0]
    for formatter_ in formatters[1:]:
        if len(formatter_(exemplar)) < len(formatter(exemplar)):
            formatter = formatter_

    return formatter


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
