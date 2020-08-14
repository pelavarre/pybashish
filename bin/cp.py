#!/usr/bin/env python3

"""
usage: cp.py [-h] [-i] [-p] [-R] FILE

duplicate a file

positional arguments:
  FILE        the file to duplicate

optional arguments:
  -h, --help  show this help message and exit
  -i          ask before replacing some other file
  -p          copy the permissions of the file too, not just its bytes
  -R          copy the dirs and files inside a dir too, don't just give up on it

bugs:
  acts like "cp -h" if called without the "-i" and "-p" args, unlike Bash "cp"
  runs ahead and works with me, without mandating that I name the duplicate, unlike Bash "cp"

examples:
  cp -  # creates copy of Stdin named "stdin~1", then "stdin~2", etc
  cp /dev/null  # creates empty file named "null~1", etc
  cp original  # creates backup named "original~1", etc
"""
# FIXME: also copy from (FILE | HOSTNAME:FILE) to here, like Bash "scp" would
# FIXME: think about "cp SOURCE TARGET" vs "cp TARGET SOURCE" vs line-editor's

import argdoc


def main():
    args = argdoc.parse_args()
    print(args)


if __name__ == "__main__":
    main()


# copied from:  git clone https://github.com/pelavarre/pybashish.git
