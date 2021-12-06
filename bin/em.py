#!/usr/bin/env python3

"""
usage: em.py [-h] ...

read files, accept edits, write files

optional arguments:
  -h, --help  show this help message and exit

how to get Em Py:
  R=pelavarre/pybashish/master/bin/vi.py
  curl -sSO --location https://raw.githubusercontent.com/$R
  echo cp -ip vi_py em_py |tr _ . ||bash
  python3 em?py em?py
  ⌃Segg

how to get Em Py again:
  python3 em?py --pwnme

how to get more help for Em Py:
  python3 em?py --help
"""

# FIXME: Emacs ⌃C escape is small 0-9a-zA-Z namespace, but ⌃C⌃C is as large as all Emacs

import sys

import vi


if __name__ == "__main__":
    vi.main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
