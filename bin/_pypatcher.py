#!/usr/bin/env python3

"""
usage: _pypatcher.py [-h] DEFNAME [FILE ...]

drop copies of a def from a first python file into other python files

positional arguments:
  DEFNAME     the name of the def to copy, such as:  stderr_print
  FILE        the file to copy from, and then the files to copy into

options:
  -h, --help  show this help message and exit

quirks:
  succeeds even when given only a file to copy from, and none to copy into
  succeeds without complaint when told to copy into the same file copied from

examples:
  _pypatcher.py stderr_print bin/cat.py $(git grep -l 'def.'stderr_print)
  _pypatcher.py subprocess_run bin/cp.py $(git grep -l 'def.'subprocess.run)
"""


import sys

import argdoc


def main(argv):
    """Run from the Command Line"""

    args = argdoc.parse_args(argv[1:])
    if not args.files:
        sys.stderr.write("_pypatcher.py: error: the FILE argument is required\n")
        sys.exit(2)  # exit 2 from rejecting usage

    fromfile = args.files[0]

    defname_pychars = copy_in_from(fromfile, defname=args.defname)
    for tofile in args.files[1:]:
        copy_out_into(tofile, defname=args.defname, defname_pychars=defname_pychars)

    # TODO: think more about kinds of Def's that don't match rf"def {defname}[(]"


def copy_in_from(fromfile, defname):
    """Pick a Def out of a Python File"""

    with open(fromfile) as reading:
        pychars = reading.read()

    defkey = "def {}(".format(defname)
    count = pychars.count(defkey)
    assert count == 1, (fromfile, defname, count)

    (start, stop) = py_defname_find(pychars, defname=defname)
    defname_pychars = pychars[start:stop]

    return defname_pychars


def copy_out_into(tofile, defname, defname_pychars):
    """Replace a Def inside a Python File"""

    with open(tofile) as reading:
        to_pychars = reading.read()

    defkey = "def {}(".format(defname)
    count = to_pychars.count(defkey)

    assert count == 1, (tofile, defname, count)

    (start, stop) = py_defname_find(pychars=to_pychars, defname=defname)
    merged_pychars = to_pychars[:start] + defname_pychars + to_pychars[stop:]

    if merged_pychars != to_pychars:

        sys.stderr.write("{}\n".format(tofile))
        with open(tofile, "w") as writing:
            writing.write(merged_pychars)


def py_defname_find(pychars, defname):
    """Return the (Start, Stop) covering the Source Chars of the Def"""

    keepends_true = True

    defkey = "def {}(".format(defname)
    start = pychars.index(defkey)

    stop = start
    tail = pychars[stop:]
    line = tail.splitlines(keepends_true)[0]

    stop += len(line)

    while stop < len(pychars):
        tail = pychars[stop:]

        line = tail.splitlines(keepends_true)[0]
        if not line.strip():
            stop += len(line)

            continue

        len_dent = len(line) - len(line.lstrip())
        if len_dent:
            stop += len(line)

            continue

        break

    return (start, stop)


if __name__ == "__main__":
    main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
