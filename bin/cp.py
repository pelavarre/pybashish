#!/usr/bin/env python3

"""
usage: cp.py [-h] [-i] [-p] [-R] [FILE]

duplicate a file (make it found twice)

positional arguments:
  FILE        the file to duplicate (default: last modified in cwd)

optional arguments:
  -h, --help  show this help message and exit
  -i          ask before replacing some other file
  -p          copy the permissions of the file too, not just its bytes
  -R          copy the dirs and files inside a dir too, don't just give up on it

bugs:
  runs ahead and works, without making you name the duplicate, unlike bash "cp"
  increments the name:  such as "touch it~41 && touch it && cp.py" makes "~41" and "it" and "~42"

examples:
  cp.py  # backs up last modified file of cwd (makes it found twice)
  cp.py -  # creates copy of Stdin named "stdin~1", then "stdin~2", etc
  cp.py /dev/null  # creates empty file named "null~1", etc
  cp.py itself  # creates backup named "itself~1", etc
"""
# FIXME: also copy from (FILE | HOSTNAME:FILE) to here, like Bash "scp" would
# FIXME: think about "cp SOURCE TARGET" vs "cp TARGET SOURCE" vs line-editor's


import sys

import argdoc


def main():
    args = argdoc.parse_args()
    sys.stderr.write("{}\n".format(args))
    sys.stderr.write("{}\n".format(argdoc.format_usage().rstrip()))
    sys.stderr.write("cp.py: error: not implemented\n")
    sys.exit(2)  # exit 2 from rejecting usage


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
