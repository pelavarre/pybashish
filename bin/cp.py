#!/usr/bin/env python3

"""
usage: cp.py [-h] [-i] [-p] [-R] [FILE]

duplicate a file (make it found twice)

positional arguments:
  FILE        the file to duplicate (default: last modified in cwd, else '/dev/null')

optional arguments:
  -h, --help  show this help message and exit
  -i          ask before replacing some other file
  -p          copy the permissions of the file too, not just its bytes
  -R          copy dirs (and the dirs and files inside the dirs)

quirks:
  chooses new file names like Emacs would:  'null', 'null~', 'null~2~', ...
  copies without changing the name, when the Cwd doesn't contain the name
  copies from hostname:path on request, but defaults to copy from Localhost
  copies always in the way of 'cp -ipR'

examples:
  cp.py  # backs up last modified file of cwd (makes it found twice)
  cp.py -  # creates copy of Stdin named "stdin~", then "stdin~2~", etc
  cp.py localhost:/etc/passwd  # backs up a file from a remote host on request
"""


import argparse
import glob
import os
import re
import shlex
import subprocess
import sys

import argdoc


def main():

    args = argdoc.parse_args()

    # Pick a FromPath to copy from
    frompath = os_path_choose() if (args.file is None) else args.file

    # Pick a ToName to copy to

    (_, basename) = os.path.split(frompath)
    (base, _, _) = os_path_partition(basename)
    toname = os_path_nextname(basename=base)

    # Copy and touch

    cp_shline = "cp -ipR {} {}".format(frompath, toname)
    if frompath == "/dev/null":
        cp_shline = "cp -i {} {}".format(frompath, toname)
    elif ":" in frompath:
        cp_shline = "scp -pqr {} {}".format(frompath, toname)

    touch_shline = "touch {}".format(toname)

    for shline in (cp_shline, touch_shline):

        shargv = shlex.split(shline)
        sys.stderr.write("+ {}\n".format(shline))
        subprocess_run(shargv, stdin=subprocess.PIPE, check=True)


# deffed in many files  # missing from docs.python.org
def os_path_choose():
    """Find the last modified, else highest name, else '/dev/null' in the Cwd"""

    paths = os.listdir()
    paths.sort(key=lambda _: os.stat(_).st_mtime)

    if not paths:

        return "/dev/null"

    path = paths[-1]

    return path


# deffed in many files  # missing from docs.python.org
def os_path_intrev(path):
    """Pick the Rev Int out of a Path"""

    (_, _, rev) = os_path_partition(path)
    intrev = os_path_rev_eval(rev, default=0)

    return intrev


# deffed in many files  # missing from docs.python.org
def os_path_nextname(basename):
    """Pick the next Filename not already existing in the Cwd"""

    pattern = basename + "*"

    paths = list(glob.glob(pattern))

    last_path = basename
    if not paths:

        return basename

    paths.sort(key=os_path_intrev)
    last_path = paths[-1]

    (base, ext, _) = os_path_partition(last_path)
    last_intrev = os_path_intrev(last_path)
    next_intrev = last_intrev + 1

    next_path = "{}{}~".format(base, ext)
    if next_intrev != 1:
        next_path = "{}{}~{}~".format(base, ext, next_intrev)

    return next_path


# deffed in many files  # missing from docs.python.org
def os_path_partition(path):
    """Pick apart the Base, the Ext, and the Rev"""

    (dirname, basename) = os.path.split(path)
    (base_plus, ext_plus) = os.path.splitext(basename)

    base = base_plus
    ext = ext_plus
    rev = ""

    if "~" in ext_plus:

        splits = ext_plus.split("~")
        ext = splits[0]

        rev = "~" + "~".join(splits[1:])

    elif (not ext_plus) and ("~" in base_plus):

        splits = base_plus.split("~")
        base = splits[0]

        rev = "~" + "~".join(splits[1:])

    assert (base + ext + rev) == basename, (base, ext, rev, path)

    return (os.path.join(dirname, base), ext, rev)


# deffed in many files  # missing from docs.python.org
def os_path_rev_eval(rev, default):
    """Pick the Rev Int out of the Rev Str"""

    int_rev = default
    if "~" in rev:
        int_rev = 1
        match = re.match(r"^~([0-9]+)~?$", string=rev)
        if match:
            int_rev = int(match.group(1))

    return int_rev  # such as 7 from "it~7~" or from "it~7"


# deffed in many files  # since Sep/2015 Python 3.5
def subprocess_run(args, **kwargs):
    """
    Emulate Python 3 "subprocess.run"

    Don't help the caller remember to say:  stdin=subprocess.PIPE
    """

    # Trust the library, if available

    if hasattr(subprocess, "run"):
        run = subprocess.run(args, **kwargs)  # pylint: disable=subprocess-run-check

        return run

    # Emulate the library roughly, because often good enough

    kwargs_ = dict(**kwargs)  # args, cwd, stdin, stdout, stderr, shell, ...

    if "check" in kwargs:
        del kwargs_["check"]

    if ("input" in kwargs) and ("stdin" in kwargs):
        raise ValueError("stdin and input arguments may not both be used.")

    if "input" in kwargs:
        raise NotImplementedError("subprocess.run.input")

    sub = subprocess.Popen(args, **kwargs_)  # pylint: disable=consider-using-with
    (stdout, stderr) = sub.communicate()
    returncode = sub.poll()

    if "check" in kwargs:
        if returncode != 0:

            raise subprocess.CalledProcessError(
                returncode=returncode, cmd=args, output=stdout
            )

    run = argparse.Namespace(
        args=args, stdout=stdout, stderr=stderr, returncode=returncode
    )

    return run


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
