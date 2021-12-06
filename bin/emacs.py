#!/usr/bin/env python3

"""
usage: emacs.py [-h] ...

read files, accept edits, write files

optional arguments:
  -h, --help  show this help message and exit

how to get Emacs Py:
  R=pelavarre/pybashish/master/bin/vi.py
  curl -sSO --location https://raw.githubusercontent.com/$R
  echo cp -ip vi_py emacs_py |tr _ . ||bash
  python3 emacs?py emacs?py
  ⌃Segg

how to get Emacs Py again:
  python3 emacs?py --pwnme

how to get more help for EMacs:
  python3 emacs?py --help
"""

# FIXME: Emacs ⌃C escape is small 0-9a-zA-Z namespace, but ⌃C⌃C is as large as all Emacs

import sys

import vi


if __name__ == "__main__":
    vi.main(sys.argv)


# copied from:  git clone https://github.com/pelavarre/pybashish.git
