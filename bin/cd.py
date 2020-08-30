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

    # Parse args

    args = argdoc.parse_args()

    if (args.dir is None) or (args.dir == "~"):
        path = os.environ["HOME"]
    elif args.dir == "-":
        try:
            path = os.environ["OLDPWD"]
        except KeyError:
            sys.stderr.write("cd.py: error: OLDPWD not set\n")
            sys.exit(1)  # classic exit status 1 for violating this env var precondition
    else:
        path = args.dir
        if args.dir.startswith("~"):
            path = os.environ["HOME"] + args.dir[1:]

    dry_run_cd(path, args=args)


def dry_run_cd(path, args):
    """Dry run a call of "os.chdir" inside this process, don't change parent process"""

    # Sample cwd

    try:
        before_cwd = os.getcwd()
    except FileNotFoundError:
        before_cwd = None

        if args.dir == "-":
            sys.stderr.write(
                "cd.py: warning: cannot access {!r}: stale file handle {}\n".format(
                    ".", "of deleted dir"
                )
            )

    before_realpath = None
    if before_cwd is not None:
        before_realpath = os.path.realpath(before_cwd)
        os.environ[
            "OLDPWD"
        ] = before_realpath  # unneeded, unless this raises an exception

    # Change cwd and resample cwd

    try:
        os.chdir(path)
        after_cwd = os.getcwd()
    except FileNotFoundError as exc:
        sys.stderr.write("cd.py: error: {}: {}\n".format(type(exc).__name__, exc))
        sys.exit(1)

    after_realpath = os.path.realpath(after_cwd)

    if args.dir == "-":
        if before_realpath == after_realpath:
            sys.stderr.write("cd.py: error: new dir is old dir\n")
            sys.exit(1)

    # Declare success

    print(after_realpath)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
