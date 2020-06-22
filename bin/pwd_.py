#!/usr/bin/env python3

"""
usage: pwd.py [-h] [-H] [-L] [-P]

optional arguments:
  -h, --help      show this help message and exit
  -H, --homepath  print as '~/...' relative to the 'os.environ["HOME"]', a la Bash 'dirs + 0'
  -L, --logical   print the 'os.path.abspath' of the 'os.getcwd'
  -P, --physical  print the 'os.path.realpath' of the 'os.getcwd'
"""


import os

import argdoc


def main():

    args = argdoc.parse_args()

    cwd = os.environ["PWD"]
    abspath = os.path.abspath(cwd)
    realpath = os.path.realpath(cwd)

    cwd = os.getcwd()
    assert cwd == realpath

    path = realpath if args.physical else abspath
    printable = os_path_homepath(path) if args.homepath else path

    print(printable)


def os_path_homepath(path):

    home = os.path.realpath(os.environ["HOME"])
    homepath = path
    if (path == home) or path.startswith(home + os.path.sep):
        homepath = "~" + os.path.sep + os.path.relpath(path, start=home)

    return homepath


if __name__ == "__main__":
    main()


# pulled from:  git clone https://github.com/pelavarre/pybashish.git
