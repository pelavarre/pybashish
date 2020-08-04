#!/usr/bin/env python3

"""
usage: tar.py [-h] [-x] [-t] [-v] [-k] [-f FILE]

pick files and dirs out of a top dir compressed as ".tgz"

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
  lists to Stderr, not to classic Stdout
  extracts to Stdout, not to the Tgz member name

examples:
  rm -fr dir/ dir.tgz
  mkdir -p dir/a/b/c dir/p/q/r
  echo hello >dir/a/b/d
  echo goodbye > dir/a/b/e
  tar czf dir.tgz dir/
  tar.py tvf dir.tgz
  tar.py xvkf dir.tgz | wc  # 2 lines, 2 words, 14 bytes
"""

import os
import sys
import tarfile

import argdoc


def main(argv):

    # Parse the command line

    parseables = list(argv[1:])
    if argv[1:] and not argv[1].startswith("-"):
        parseables[0] = "-{}".format(argv[1])

    args = argdoc.parse_args(parseables)

    tvf = args.t and args.v and args.file
    xvkf = args.x and args.v and args.k and args.file
    assert tvf or xvkf

    # Visit each dir or file inside the Tar file

    with tarfile.open(args.file) as untarring:

        names = untarring.getnames()
        for name in names:
            member = untarring.getmember(name)

            # Trace the visit

            if member.isdir():
                print(name + os.sep, file=sys.stderr)
            else:
                print(name, file=sys.stderr)

                # Extract the bytes of a file

                if args.x:

                    with untarring.extractfile(name) as incoming:
                        file_bytes = incoming.read()

                    os.write(sys.stdout.fileno(), file_bytes)


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
