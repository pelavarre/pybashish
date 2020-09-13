#!/usr/bin/env python3

"""
usage: tar.py [-h] [-t] [-x] [-v] [-k] [-f FILE]

walk the files and dirs found inside a top dir compressed as Tgz

optional arguments:
  -h, --help  show this help message and exit
  -t          list every file, without writing any files
  -x          write out a copy of every file
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

unsurprising bugs:
  does prompt once for stdin, like bash "grep -R", a la linux "tar ztvf -", unlike mac "tar tvf -"
  accepts only the "stty -a" line-editing c0-control's, not the "bind -p" c0-control's

bash script to compress a top dir as Tgz for test:
  rm -fr dir/ dir.tgz
  mkdir -p dir/a/b/c dir/p/q/r
  echo hello >dir/a/b/d
  echo goodbye > dir/a/b/e
  tar czf dir.tgz dir/
  rm -fr dir/

examples:
  tar.py tvf dir.tgz
  tar.py xvkf dir.tgz | wc  # 2 lines, 2 words, 14 bytes
  tar.py -tvf /dev/null/child -tvf dir.tgz  # first args discarded, last args obeyed
"""


import os
import sys
import tarfile

import argdoc


LIMITED_USAGE = "usage: tar.py [-h] (-tvf|-xvkf) FILE"


def main(argv):
    """Interpret a command line"""

    # Parse the command line

    tar_argv_tail = list(argv[1:])
    if argv[1:] and not argv[1].startswith("-"):
        tar_argv_tail[0] = "-{}".format(argv[1])

    args = argdoc.parse_args(tar_argv_tail if tar_argv_tail else "--help".split())

    # Require -tvf or -xvkf

    tvf = args.t and args.v and args.file
    xvkf = args.x and args.v and args.k and args.file
    if not (tvf or xvkf):
        stderr_print_usage_error(args)
        sys.exit(2)  # exit 2 from rejecting usage

    # Interpret -tvf or -xvkf

    args_file = args.file
    if args.file == "-":
        args_file = "/dev/stdin"
        prompt_tty_stdin()

    tar_file_tvf_xvkf(args_file, args_x=args.x)


def stderr_print_usage_error(args):
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

    stderr_print(LIMITED_USAGE)
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

                    # Python 2:  with contextlib.closing(untarring.extractfile(name)) as incoming:
                    with untarring.extractfile(name) as incoming:
                        file_bytes = incoming.read()

                    os.write(sys.stdout.fileno(), file_bytes)


#
# Git-track some Python idioms here
#


# deffed in many files  # missing from docs.python.org
def prompt_tty_stdin():
    if sys.stdin.isatty():
        stderr_print("Press ⌃D EOF to quit")


# deffed in many files  # missing from docs.python.org
def stderr_print(*args, **kwargs):
    sys.stdout.flush()
    print(*args, **kwargs, file=sys.stderr)
    sys.stderr.flush()  # esp. when kwargs["end"] != "\n"


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
