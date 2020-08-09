#!/usr/bin/env python3

"""
usage: tar.py [-h] [-x] [-t] [-v] [-k] [-f FILE]

walk the files and dirs found inside a top dir compressed as Tgz

optional arguments:
  -h, --help  show this help message and exit
  -x          extract every file
  -t          say it loud, you have not chosen -x
  -v          trace each file or dir name found inside to Stderr
  -k          decline to replace pre-existing output files
  -f FILE     name the file to uncompress

bugs:
  accepts only -tvf and -tvkf as options
  lets you type out just "tvf" or "tvkf" without their leading "-" dash
  prints only the name for -tvf, not all the "ls -al" columns
  prints all the dirs for -tvf, not only the top dir
  prints names found inside to stderr, not to classic stdout
  extracts always to stdout, never to the name found inside

bash script to compress a top dir as Tgz for test:
  rm -fr dir/ dir.tgz
  mkdir -p dir/a/b/c dir/p/q/r
  echo hello >dir/a/b/d
  echo goodbye > dir/a/b/e
  tar czf dir.tgz dir/

examples:
  tar.py tvf dir.tgz
  tar.py xvkf dir.tgz | wc  # 2 lines, 2 words, 14 bytes
  tar.py -tvf /dev/null/child -tvf dir.tgz  # first args discarded, last args obeyed
"""

import os
import sys
import tarfile

import argdoc


LIMITED_USAGE = "usage: tar.py: [-h] (-tvf|xvkf) FILE"


def main(argv):
    """Interpret a command line"""

    # Parse the command line

    parseables = list(argv[1:])
    if argv[1:] and not argv[1].startswith("-"):
        parseables[0] = "-{}".format(argv[1])

    args = argdoc.parse_args(parseables if parseables else "--help".split())

    # Require -tvf or -xvkf

    tvf = args.t and args.v and args.file
    xvkf = args.x and args.v and args.k and args.file
    if not (tvf or xvkf):
        print_limited_usage(args)
        sys.exit(2)  # exit 2 from rejecting usage

    # Interpret -tvf or -xvkf

    tar_file_tvf_xvkf(args.file, args_x=args.x)


def print_limited_usage(args):
    """Limit to usage: [-h] (-tvf|xvkf) FILE"""

    # List how much of -tvf and -xvkf supplied

    str_args = ""
    for concise in "txvk":
        if getattr(args, concise):
            str_args += concise
    if args.file is not None:
        str_args += "f"
    str_args = "-{}".format(str_args) if str_args else ""

    # Demand more

    stderr_print("usage: tar.py: [-h] (-tvf|xvkf) FILE")
    if not str_args:
        stderr_print("tar.py: error: too few arguments")
    else:
        stderr_print("tar.py: error: unrecognized arguments: {}".format(str_args))


def tar_file_tvf_xvkf(args_file, args_x):
    """Walk the files and dirs found inside a top dir compressed as Tgz"""

    # Walk to each file or dir found inside

    with tarfile.open(args_file) as untarring:  # tarfile.TarFile

        names = untarring.getnames()
        for name in names:
            member = untarring.getmember(name)

            # Trace the walk

            if member.isdir():
                print(name + os.sep, file=sys.stderr)
            else:
                print(name, file=sys.stderr)

                # Option to extract the bytes of the files

                if args_x:

                    # with untarring.extractfile(name) as incoming:
                    with untarring.extractfile(name) as incoming:
                        file_bytes = incoming.read()

                    os.write(sys.stdout.fileno(), file_bytes)


# deffed in many files  # but not in docs.python.org
def stderr_print(*args):
    print(*args, file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
