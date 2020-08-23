#!/usr/bin/env python3

"""
usage: cd.py [-h] [DIR]

dry run injecting a change of working dir

positional arguments:
  DIR         the directory to work in next (default: $HOME)

optional arguments:
  -h, --help  show this help message and exit

bugs:
  prints the working dir found as a dry run, doesn't change the working dir in the calling process
  fails "cd -" if old dir is same as new dir, unlike bash
  fails "cd -" if called before some other "cd" backs up a dir name as $OLDPWD, unlike zsh

examples:
  cd  # go home
  cd -  # go back
  cd ~  # go home by name
  cd /  # go to top
  cd .  # go to nowhere different
  cd ..  # go up
"""


import os
import sys

import argdoc


def main():

    args = argdoc.parse_args()

    if (args.dir is None) or (args.dir == "~"):
        relpath = os.environ["HOME"]
    elif args.dir == "-":
        try:
            relpath = os.environ["OLDPWD"]
        except KeyError:
            sys.stderr.write("cd.py: error: OLDPWD not set\n")
            sys.exit(1)  # classic exit status 1 for violating this env var precondition
    else:
        relpath = args.dir
        if args.dir.startswith("~"):
            relpath = os.environ["HOME"] + args.dir[1:]

    before_realpath = os.path.realpath(os.getcwd())
    os.environ["OLDPWD"] = before_realpath  # unneeded, unless this raises an exception

    os.chdir(relpath)
    after_realpath = os.path.realpath(os.getcwd())

    if args.dir == "-":
        if before_realpath == after_realpath:
            sys.stderr.write("cd.py: error: new dir is old dir\n")
            sys.exit(1)

    print(after_realpath)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
